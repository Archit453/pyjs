"""Bytecode compiler for PyJS (Phase 4 + Phase 5 scope).

Consumes the Phase 3 AST and emits a CodeObject (bytecode + constants +
metadata). Faithful to the frozen architecture:

  * one Compiler instance per function body; the top-level script is the root
    body and ends in HALT
  * scope resolution via SymbolTable (LOCAL slot / UPVALUE index / GLOBAL
    name)
  * stores LEAVE their value; expression statements emit a trailing POP
  * jump/loop/switch patching via CodeObject.patch_jump
  * a tagged control-context stack distinguishes LOOP (break+continue) from
    SWITCH (break only)

Phase 4 implements: variables (let/const/assignment), literals, arithmetic,
comparison, logical, unary, if/else, while, do-while, for, switch, break,
continue.

Phase 5 adds: function declarations, function expressions, arrow functions,
return statements, call expressions, recursion, closures and upvalues.
A function body is compiled by a *child* Compiler whose SymbolTable links to
the enclosing one; captured variables become upvalues (closed over via
MAKE_CLOSURE at runtime). Arrays/objects/methods are later phases and raise a
clear CompileError if encountered.
"""
from ..pyjs_ast import ast_nodes as A
from ..vm.opcode import OpCode as Op
from ..vm.instruction import CodeObject
from ..runtime.values import JSFunction
from .symbol_table import (
    SymbolTable, LOCAL, UPVALUE, GLOBAL, LET, CONST, FUNCTION, PARAM,
)


class CompileError(Exception):
    def __init__(self, message, line=0):
        super().__init__(f"{message}" + (f" (line {line})" if line else ""))
        self.raw_message = message
        self.line = line


# Control-context kinds.
_LOOP = "loop"
_SWITCH = "switch"


class _Context:
    """A breakable/continuable control context for patching jumps."""

    __slots__ = ("kind", "break_patches", "continue_patches")

    def __init__(self, kind):
        self.kind = kind
        self.break_patches = []       # jump-instruction indices to patch to end
        self.continue_patches = []    # jump-instruction indices (loops only)


_BINARY_OPS = {
    "+": Op.ADD, "-": Op.SUB, "*": Op.MUL, "/": Op.DIV, "%": Op.MOD,
    "**": Op.POW,
    "==": Op.EQ, "!=": Op.NEQ, "===": Op.STRICT_EQ, "!==": Op.STRICT_NEQ,
    ">": Op.GT, "<": Op.LT, ">=": Op.GTE, "<=": Op.LTE,
}


class Compiler:
    def __init__(self, enclosing=None, name="<script>", is_script=True):
        self.enclosing = enclosing
        self.code = CodeObject(name=name)
        self.symbols = SymbolTable(
            enclosing=enclosing.symbols if enclosing else None)
        self.is_script = is_script
        self.contexts = []            # stack of _Context

    # -- public entry --
    def compile_program(self, program):
        for stmt in program.body:
            self._statement(stmt)
        self.code.emit(Op.HALT)
        self.code.num_locals = self.symbols.max_slots
        return self.code

    # -- helpers --
    def _emit(self, op, operand=None, line=0):
        return self.code.emit(op, operand, line)

    def _name_const(self, name):
        return self.code.add_const(name)

    def _is_global_scope(self):
        return self.is_script and self.symbols.scope_depth == 0

    def _begin_scope(self):
        self.symbols.begin_scope()

    def _end_scope(self):
        popped = self.symbols.end_scope()
        # Close any captured locals leaving this scope so their upvalues become
        # closed (survive after the slot is reclaimed). Innermost-first.
        for sym in popped:
            if sym.is_captured:
                self._emit(Op.CLOSE_UPVALUE, sym.slot)
        return popped

    # ----------------------------------------------------------- statements
    def _statement(self, node):
        m = getattr(self, "_stmt_" + type(node).__name__, None)
        if m is None:
            raise CompileError(
                f"Unsupported statement {type(node).__name__}",
                getattr(node, "line", 0))
        m(node)

    def _stmt_VarDecl(self, node):
        kind = CONST if node.kind == "const" else LET
        if self._is_global_scope():
            if node.init is not None:
                self._expression(node.init)
            else:
                self._emit(Op.LOAD_UNDEFINED, line=node.line)
            idx = self._name_const(node.name)
            self._emit(Op.DEFINE_GLOBAL, idx, line=node.line)
            if kind == CONST:
                self.code.const_globals.add(node.name)
        else:
            # Local: declare the slot FIRST so a self-referential function
            # expression (and recursion via name) can resolve it, then
            # evaluate the initializer into that slot.
            sym = self.symbols.declare(node.name, kind)
            if node.init is not None:
                self._expression(node.init)
            else:
                self._emit(Op.LOAD_UNDEFINED, line=node.line)
            self._emit(Op.STORE_LOCAL, sym.slot, line=node.line)
            self._emit(Op.POP, line=node.line)

    def _stmt_ExpressionStmt(self, node):
        self._expression(node.expr)
        self._emit(Op.POP, line=node.line)

    def _stmt_Block(self, node):
        self._begin_scope()
        for stmt in node.body:
            self._statement(stmt)
        self._end_scope()

    def _stmt_IfStmt(self, node):
        self._expression(node.test)
        else_jump = self._emit(Op.JUMP_IF_FALSE, 0, line=node.line)
        self._statement(node.consequent)
        if node.alternate is not None:
            end_jump = self._emit(Op.JUMP, 0, line=node.line)
            self.code.patch_jump(else_jump)
            self._statement(node.alternate)
            self.code.patch_jump(end_jump)
        else:
            self.code.patch_jump(else_jump)

    def _stmt_WhileStmt(self, node):
        ctx = _Context(_LOOP)
        self.contexts.append(ctx)
        loop_start = self.code.here()
        self._expression(node.test)
        exit_jump = self._emit(Op.JUMP_IF_FALSE, 0, line=node.line)
        self._statement(node.body)
        self._emit(Op.JUMP, loop_start, line=node.line)
        self.code.patch_jump(exit_jump)
        self.contexts.pop()
        for p in ctx.break_patches:
            self.code.patch_jump(p)
        for p in ctx.continue_patches:
            self.code.patch_jump(p, loop_start)

    def _stmt_DoWhileStmt(self, node):
        ctx = _Context(_LOOP)
        self.contexts.append(ctx)
        body_start = self.code.here()
        self._statement(node.body)
        cond_start = self.code.here()
        self._expression(node.test)
        self._emit(Op.JUMP_IF_TRUE, body_start, line=node.line)
        self.contexts.pop()
        for p in ctx.break_patches:
            self.code.patch_jump(p)
        for p in ctx.continue_patches:
            self.code.patch_jump(p, cond_start)

    def _stmt_ForStmt(self, node):
        self._begin_scope()
        if node.init is not None:
            if isinstance(node.init, A.VarDecl):
                self._for_init_decl(node.init)
            else:
                self._statement(node.init)
        ctx = _Context(_LOOP)
        self.contexts.append(ctx)
        loop_start = self.code.here()
        exit_jump = None
        if node.test is not None:
            self._expression(node.test)
            exit_jump = self._emit(Op.JUMP_IF_FALSE, 0, line=node.line)
        self._statement(node.body)
        update_start = self.code.here()
        if node.update is not None:
            self._expression(node.update)
            self._emit(Op.POP, line=node.line)
        self._emit(Op.JUMP, loop_start, line=node.line)
        if exit_jump is not None:
            self.code.patch_jump(exit_jump)
        self.contexts.pop()
        for p in ctx.break_patches:
            self.code.patch_jump(p)
        for p in ctx.continue_patches:
            self.code.patch_jump(p, update_start)
        self._end_scope()

    def _for_init_decl(self, node):
        kind = CONST if node.kind == "const" else LET
        sym = self.symbols.declare(node.name, kind)
        if node.init is not None:
            self._expression(node.init)
        else:
            self._emit(Op.LOAD_UNDEFINED, line=node.line)
        self._emit(Op.STORE_LOCAL, sym.slot, line=node.line)
        self._emit(Op.POP, line=node.line)

    def _stmt_SwitchStmt(self, node):
        ctx = _Context(_SWITCH)
        self._expression(node.discriminant)
        temp = self.symbols.reserve_slot()
        self._emit(Op.STORE_LOCAL, temp, line=node.line)
        self._emit(Op.POP, line=node.line)
        self.contexts.append(ctx)
        body_jumps = []
        default_index = None
        for i, case in enumerate(node.cases):
            if case.test is None:
                default_index = i
                continue
            self._emit(Op.LOAD_LOCAL, temp, line=case.line)
            self._expression(case.test)
            self._emit(Op.STRICT_EQ, line=case.line)
            jmp = self._emit(Op.JUMP_IF_TRUE, 0, line=case.line)
            body_jumps.append((i, jmp))
        default_jump = self._emit(Op.JUMP, 0, line=node.line)
        body_starts = {}
        for i, case in enumerate(node.cases):
            body_starts[i] = self.code.here()
            for stmt in case.body:
                self._statement(stmt)
        end = self.code.here()
        for i, jmp in body_jumps:
            self.code.patch_jump(jmp, body_starts[i])
        if default_index is not None:
            self.code.patch_jump(default_jump, body_starts[default_index])
        else:
            self.code.patch_jump(default_jump, end)
        self.contexts.pop()
        self.symbols.release_slot()
        for p in ctx.break_patches:
            self.code.patch_jump(p, end)

    def _stmt_BreakStmt(self, node):
        ctx = self._nearest_context(any_kind=True)
        if ctx is None:
            raise CompileError("'break' outside loop or switch", node.line)
        jmp = self._emit(Op.JUMP, 0, line=node.line)
        ctx.break_patches.append(jmp)

    def _stmt_ContinueStmt(self, node):
        ctx = self._nearest_context(any_kind=False)
        if ctx is None:
            raise CompileError("'continue' outside loop", node.line)
        jmp = self._emit(Op.JUMP, 0, line=node.line)
        ctx.continue_patches.append(jmp)

    def _nearest_context(self, any_kind):
        for ctx in reversed(self.contexts):
            if any_kind or ctx.kind == _LOOP:
                return ctx
        return None

    # ------------------------------------------------- functions (Phase 5)
    def _stmt_FunctionDecl(self, node):
        # Declare the name BEFORE compiling the body so the function can call
        # itself (recursion) and so the binding exists for later statements.
        if self._is_global_scope():
            self._compile_function(node, node.name)
            idx = self._name_const(node.name)
            self._emit(Op.DEFINE_GLOBAL, idx, line=node.line)
        else:
            sym = self.symbols.declare(node.name, FUNCTION)
            self._compile_function(node, node.name)
            self._emit(Op.STORE_LOCAL, sym.slot, line=node.line)
            self._emit(Op.POP, line=node.line)

    def _stmt_ReturnStmt(self, node):
        if node.value is not None:
            self._expression(node.value)
        else:
            self._emit(Op.LOAD_UNDEFINED, line=node.line)
        self._emit(Op.RETURN, line=node.line)

    def _expr_FunctionExpr(self, node):
        name = node.name or "<anonymous>"
        self._compile_function(node, name)

    def _compile_function(self, node, name):
        """Compile a function/arrow body with a child Compiler, store the
        resulting JSFunction in the constant pool, and emit MAKE_CLOSURE with
        the captured upvalue descriptors."""
        sub = Compiler(enclosing=self, name=name, is_script=False)
        is_arrow = getattr(node, "is_arrow", False)

        params = list(node.params or [])
        for p in params:
            sub.symbols.declare(p, PARAM)
        rest = getattr(node, "rest", None)
        if rest:
            sub.symbols.declare(rest, PARAM)

        body = node.body
        if isinstance(body, A.Block):
            for stmt in body.body:
                sub._statement(stmt)
            sub._emit(Op.LOAD_UNDEFINED)
            sub._emit(Op.RETURN)
        elif isinstance(body, list):
            for stmt in body:
                sub._statement(stmt)
            sub._emit(Op.LOAD_UNDEFINED)
            sub._emit(Op.RETURN)
        else:
            # Arrow with expression body: `(a) => a + 1`
            sub._expression(body)
            sub._emit(Op.RETURN)

        sub.code.arity = len(params)
        sub.code.has_rest = bool(rest)
        sub.code.num_locals = sub.symbols.max_slots
        sub.code.upvalues = list(sub.symbols.upvalues)

        fn = JSFunction(sub.code, is_arrow=is_arrow)
        const_idx = self.code.add_const(fn)
        self._emit(Op.MAKE_CLOSURE, const_idx, line=getattr(node, "line", 0))

    def _has_spread(self, args):
        return any(isinstance(a, A.SpreadElement) for a in args)

    def _expr_CallExpr(self, node):
        callee = node.callee
        if isinstance(callee, A.MemberExpr):
            self._method_call(node, callee)
            return
        # Plain call. Protocol: push callee, push this(undefined), push args.
        self._expression(callee)
        self._emit(Op.LOAD_UNDEFINED, line=node.line)   # this
        if self._has_spread(node.args):
            self._build_args_array(node.args)
            self._emit(Op.CALL_SPREAD, 0, line=node.line)
        else:
            for arg in node.args:
                self._expression(arg)
            self._emit(Op.CALL, len(node.args), line=node.line)

    def _method_call(self, node, callee):
        # obj.method(args): evaluate obj once, keep it as `this`, fetch the
        # method as the callee. Stack: [method, obj, args...].
        self._expression(callee.obj)              # receiver (this)
        self._emit(Op.DUP, line=node.line)        # [obj, obj]
        # fetch method off the duplicated receiver
        if callee.computed:
            self._expression(callee.prop)         # [obj, obj, key]
            self._emit(Op.GET_INDEX, line=node.line)   # [obj, method]
        else:
            idx = self._name_const(callee.prop)
            self._emit(Op.GET_PROP, idx, line=node.line)  # [obj, method]
        # Now reorder to [method, this] using SWAP-free trick: we have
        # [obj, method]; emit SWAP via DUP/rotate is unavailable, so use the
        # dedicated CALL_METHOD which expects [receiver, method, args...].
        if self._has_spread(node.args):
            self._build_args_array(node.args)
            self._emit(Op.CALL_SPREAD, 1, line=node.line)
        else:
            for arg in node.args:
                self._expression(arg)
            self._emit(Op.CALL_METHOD, len(node.args), line=node.line)

    def _build_args_array(self, args):
        # Build a single JSArray of all positional args, expanding spreads.
        count = 0
        for a in args:
            if isinstance(a, A.SpreadElement):
                self._expression(a.argument)
                self._emit(Op.SPREAD, line=getattr(a, "line", 0))
            else:
                self._expression(a)
            count += 1
        self._emit(Op.BUILD_ARRAY_SPREAD, count, line=0)

    # ---------------------------------------------------------- expressions
    def _expression(self, node):
        m = getattr(self, "_expr_" + type(node).__name__, None)
        if m is None:
            raise CompileError(
                f"Unsupported expression {type(node).__name__}",
                getattr(node, "line", 0))
        m(node)

    def _expr_NumberLiteral(self, node):
        self._emit(Op.LOAD_CONST, self.code.add_const(node.value), line=node.line)

    def _expr_StringLiteral(self, node):
        self._emit(Op.LOAD_CONST, self.code.add_const(node.value), line=node.line)

    def _expr_BooleanLiteral(self, node):
        self._emit(Op.LOAD_TRUE if node.value else Op.LOAD_FALSE, line=node.line)

    def _expr_NullLiteral(self, node):
        self._emit(Op.LOAD_NULL, line=node.line)

    def _expr_UndefinedLiteral(self, node):
        self._emit(Op.LOAD_UNDEFINED, line=node.line)

    def _expr_Identifier(self, node):
        # `this` is parsed as a bare identifier; resolve it to the current
        # frame's receiver rather than a global lookup.
        if node.name == "this":
            self._emit(Op.LOAD_THIS, line=node.line)
            return
        kind, payload = self.symbols.resolve(node.name)
        if kind == LOCAL:
            self._emit(Op.LOAD_LOCAL, payload.slot, line=node.line)
        elif kind == UPVALUE:
            self._emit(Op.LOAD_UPVALUE, payload, line=node.line)
        else:
            self._emit(Op.LOAD_GLOBAL, self._name_const(node.name), line=node.line)

    def _expr_BinaryExpr(self, node):
        op = _BINARY_OPS.get(node.op)
        if op is None:
            raise CompileError(f"Unknown binary operator {node.op}", node.line)
        self._expression(node.left)
        self._expression(node.right)
        self._emit(op, line=node.line)

    def _expr_LogicalExpr(self, node):
        self._expression(node.left)
        if node.op == "&&":
            short = self._emit(Op.JUMP_IF_FALSE_KEEP, 0, line=node.line)
            self._emit(Op.POP, line=node.line)
            self._expression(node.right)
            self.code.patch_jump(short)
        else:  # ||
            short = self._emit(Op.JUMP_IF_TRUE_KEEP, 0, line=node.line)
            self._emit(Op.POP, line=node.line)
            self._expression(node.right)
            self.code.patch_jump(short)

    def _expr_UnaryExpr(self, node):
        if node.op == "!":
            self._expression(node.operand)
            self._emit(Op.NOT, line=node.line)
        elif node.op == "-":
            self._expression(node.operand)
            self._emit(Op.NEG, line=node.line)
        elif node.op == "+":
            self._expression(node.operand)
            self._emit(Op.LOAD_CONST, self.code.add_const(1.0), line=node.line)
            self._emit(Op.MUL, line=node.line)
        elif node.op == "typeof":
            self._expression(node.operand)
            self._emit(Op.TYPEOF, line=node.line)
        else:
            raise CompileError(f"Unknown unary operator {node.op}", node.line)

    def _expr_UpdateExpr(self, node):
        target = node.target
        if not isinstance(target, A.Identifier):
            raise CompileError("Update target must be a variable in this phase",
                               node.line)
        delta = 1.0 if node.op == "++" else -1.0
        kind, payload = self.symbols.resolve(target.name)
        self._load_name(target.name, kind, payload, node.line)
        if not node.prefix:
            self._emit(Op.DUP, line=node.line)
        self._emit(Op.LOAD_CONST, self.code.add_const(delta), line=node.line)
        self._emit(Op.ADD, line=node.line)
        self._store_name(target.name, kind, payload, node.line)
        if not node.prefix:
            self._emit(Op.POP, line=node.line)

    def _expr_AssignExpr(self, node):
        target = node.target
        if isinstance(target, A.MemberExpr):
            self._assign_member(node, target)
            return
        if not isinstance(target, A.Identifier):
            raise CompileError("Invalid assignment target", node.line)
        kind, payload = self.symbols.resolve(target.name)
        if kind == LOCAL and payload.kind == CONST:
            raise CompileError(
                f"Assignment to constant variable '{target.name}'", node.line)
        if node.op == "=":
            self._expression(node.value)
        else:  # += / -=
            self._load_name(target.name, kind, payload, node.line)
            self._expression(node.value)
            self._emit(Op.ADD if node.op == "+=" else Op.SUB, line=node.line)
        self._store_name(target.name, kind, payload, node.line)

    def _assign_member(self, node, target):
        # obj[key] = value / obj.prop = value. SET_INDEX/SET_PROP leave the
        # assigned value on the stack (assignment-as-expression).
        self._expression(target.obj)
        if target.computed:
            self._expression(target.prop)
            if node.op == "=":
                self._expression(node.value)
            else:
                # compound: load current then combine
                self._emit(Op.DUP, line=node.line)        # extra obj? handled below
                raise CompileError(
                    "Compound assignment to computed member is unsupported",
                    node.line)
            self._emit(Op.SET_INDEX, line=node.line)
        else:
            idx = self._name_const(target.prop)
            if node.op == "=":
                self._expression(node.value)
            else:
                raise CompileError(
                    "Compound assignment to member is unsupported", node.line)
            self._emit(Op.SET_PROP, idx, line=node.line)

    def _expr_SpreadElement(self, node):
        # A bare spread outside array/call context is invalid.
        raise CompileError("Unexpected spread element", getattr(node, "line", 0))

    def _expr_ArrayLiteral(self, node):
        if self._has_spread(node.elements):
            count = 0
            for el in node.elements:
                if isinstance(el, A.SpreadElement):
                    self._expression(el.argument)
                    self._emit(Op.SPREAD, line=getattr(el, "line", 0))
                else:
                    self._expression(el)
                count += 1
            self._emit(Op.BUILD_ARRAY_SPREAD, count, line=node.line)
        else:
            for el in node.elements:
                self._expression(el)
            self._emit(Op.BUILD_ARRAY, len(node.elements), line=node.line)

    def _expr_ObjectLiteral(self, node):
        for prop in node.properties:
            if prop.computed:
                self._expression(prop.key)
            else:
                self._emit(Op.LOAD_CONST, self.code.add_const(str(prop.key)),
                           line=node.line)
            self._expression(prop.value)
        self._emit(Op.BUILD_OBJECT, len(node.properties), line=node.line)

    def _expr_MemberExpr(self, node):
        self._expression(node.obj)
        if node.computed:
            self._expression(node.prop)
            self._emit(Op.GET_INDEX, line=node.line)
        else:
            idx = self._name_const(node.prop)
            self._emit(Op.GET_PROP, idx, line=node.line)

    def _expr_ConditionalExpr(self, node):
        self._expression(node.test)
        else_jump = self._emit(Op.JUMP_IF_FALSE, 0, line=node.line)
        self._expression(node.consequent)
        end_jump = self._emit(Op.JUMP, 0, line=node.line)
        self.code.patch_jump(else_jump)
        self._expression(node.alternate)
        self.code.patch_jump(end_jump)

    # -- name load/store helpers --
    def _load_name(self, name, kind, payload, line):
        if kind == LOCAL:
            self._emit(Op.LOAD_LOCAL, payload.slot, line=line)
        elif kind == UPVALUE:
            self._emit(Op.LOAD_UPVALUE, payload, line=line)
        else:
            self._emit(Op.LOAD_GLOBAL, self._name_const(name), line=line)

    def _store_name(self, name, kind, payload, line):
        if kind == LOCAL:
            self._emit(Op.STORE_LOCAL, payload.slot, line=line)
        elif kind == UPVALUE:
            self._emit(Op.STORE_UPVALUE, payload, line=line)
        else:
            self._emit(Op.STORE_GLOBAL, self._name_const(name), line=line)


def compile_program(program, name="<script>"):
    """Compile a Program AST into a CodeObject."""
    return Compiler(name=name, is_script=True).compile_program(program)


def compile_source(source, name="<script>"):
    """Lex + parse + compile a source string into a CodeObject."""
    from ..parser.parser import parse_source
    return compile_program(parse_source(source), name=name)
