"""Stack-based bytecode VM for PyJS (Phase 4 + Phase 5 scope).

Executes a CodeObject produced by the compiler. No AST is touched at runtime.
Faithful to the frozen architecture: a single value stack, a frame stack, and
locals addressed as stack[base + slot]. Globals go through Environment.

Phase 4 executes: constants, variables (local/global), arithmetic, comparison,
logical (via *_KEEP jumps), unary, control-flow jumps, DUP/POP, HALT.

Phase 5 adds first-class functions:
  * MAKE_CLOSURE  - build a JSClosure from a JSFunction constant, capturing
                    upvalues from the current frame (open) or enclosing
                    closure (already-captured).
  * CALL          - invoke a JSClosure or NativeFunctionValue. Stack layout at
                    the call site is [callee, this, arg0..argN-1]; a new
                    CallFrame is pushed with base pointing at arg0.
  * RETURN        - pop the return value, close any open upvalues at/above the
                    frame base, discard the frame's stack window (callee + this
                    + args + locals), and push the result onto the caller.
  * LOAD/STORE_UPVALUE - read/write a captured variable through its Upvalue.
  * CLOSE_UPVALUE - close the open upvalue for a local leaving scope.

The call protocol matches runtime/callframe.py:
    [ callee, this, arg0, arg1, ... argN-1, <reserved locals> ]
     base-2   base-1  base ........................
"""
from ..runtime.values import (
    UNDEFINED, NULL,
    is_truthy, to_number, js_add, js_typeof,
    js_loose_equals, js_strict_equals, js_compare,
    JSFunction, JSClosure, Upvalue, NativeFunctionValue, is_callable,
    JSObject, JSArray,
)
from ..runtime.environment import Environment, PyJSRuntimeError
from ..runtime.callframe import CallFrame
from ..runtime.members import get_member, set_member
from ..runtime import builtins as _builtins
from .opcode import OpCode as Op


MAX_FRAMES = 1000


class _Spread:
    """Runtime marker wrapping an array/string to be expanded by
    BUILD_ARRAY_SPREAD or CALL_SPREAD. Never escapes into user values."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


def _key_to_str(key):
    from ..runtime.values import to_js_string
    return to_js_string(key)


class _ScriptClosure:
    """Minimal closure wrapper so the top-level script runs in a CallFrame."""

    __slots__ = ("function", "upvalues", "this")

    def __init__(self, code):
        self.function = JSFunction(code)
        self.upvalues = []
        self.this = UNDEFINED

    @property
    def name(self):
        return self.function.name


class VM:
    def __init__(self, environment=None, install_builtins=True):
        self.env = environment or Environment()
        self.stack = []
        self.frames = []
        self.last_value = UNDEFINED   # value of the last expression statement
        # Open upvalues keyed by absolute stack index, so multiple closures
        # capturing the same live local share one Upvalue object.
        self._open_upvalues = {}
        self._const_globals = set()
        # console.log output capture (tests assert on this).
        self.console_output = []
        if install_builtins:
            _builtins.install(self.env)

    # -- stack helpers --
    def _push(self, v):
        self.stack.append(v)

    def _pop(self):
        return self.stack.pop()

    def _peek(self, distance=0):
        return self.stack[-1 - distance]

    # -- entry --
    def run(self, code):
        const_globals = getattr(code, "const_globals", set())
        closure = _ScriptClosure(code)
        base = len(self.stack)
        for _ in range(code.num_locals):
            self.stack.append(UNDEFINED)
        frame = CallFrame(closure, base, UNDEFINED)
        self.frames.append(frame)
        self._const_globals = const_globals
        try:
            self._dispatch()
        finally:
            if self.frames:
                self.frames.pop()
        return self.last_value

    # -- upvalue capture --
    def _capture_upvalue(self, stack_index):
        """Return the shared open Upvalue for an absolute stack slot."""
        existing = self._open_upvalues.get(stack_index)
        if existing is not None:
            return existing
        uv = Upvalue(self.stack, stack_index)
        self._open_upvalues[stack_index] = uv
        return uv

    def _close_upvalues_from(self, from_index):
        """Close every open upvalue whose slot is >= from_index."""
        if not self._open_upvalues:
            return
        for idx in [i for i in self._open_upvalues if i >= from_index]:
            self._open_upvalues[idx].close()
            del self._open_upvalues[idx]

    # -- public call entry (for higher-order natives / REPL) --
    def call_value(self, callee, args, this=UNDEFINED):
        """Invoke a callable from Python and run it to completion, returning the
        result. Reuses the same value stack and dispatch loop."""
        if isinstance(callee, NativeFunctionValue):
            return callee.fn(self, this, list(args))
        if not isinstance(callee, JSClosure):
            raise PyJSRuntimeError("value is not a function")
        depth_before = len(self.frames)
        self._push(callee)
        self._push(this)
        for a in args:
            self._push(a)
        self._invoke(callee, len(args))
        # Run until the freshly pushed frame returns.
        self._dispatch(stop_at_depth=depth_before)
        return self._pop()

    # -- the call mechanism --
    def _invoke(self, callee, argc, this=UNDEFINED):
        if isinstance(callee, NativeFunctionValue):
            # [callee, this, args...] -> result
            args = [self.stack[len(self.stack) - argc + i] for i in range(argc)]
            # discard callee + this + args
            del self.stack[len(self.stack) - argc - 2:]
            self._push(callee.fn(self, this, args))
            return
        if not isinstance(callee, JSClosure):
            raise PyJSRuntimeError(
                f"{js_typeof(callee)} value is not a function")
        if len(self.frames) >= MAX_FRAMES:
            raise PyJSRuntimeError("Maximum call stack size exceeded")
        fn = callee.function
        arity = fn.code.arity
        top = len(self.stack)
        base = top - argc          # points at arg0
        if fn.code.has_rest:
            # Collect extra args (and any beyond declared params) into a
            # JSArray placed in the rest param's slot (slot == arity).
            # Declared params occupy slots 0..arity-1; rest occupies `arity`.
            named = arity
            extra = self.stack[base + named:top]
            del self.stack[base + named:top]
            # pad missing named params
            while len(self.stack) - base < named:
                self.stack.append(UNDEFINED)
            self.stack.append(JSArray(list(extra)))
            filled = named + 1
            for _ in range(fn.code.num_locals - filled):
                self.stack.append(UNDEFINED)
        else:
            if argc < arity:
                for _ in range(arity - argc):
                    self.stack.append(UNDEFINED)
            elif argc > arity:
                del self.stack[base + arity:top]
            for _ in range(fn.code.num_locals - arity):
                self.stack.append(UNDEFINED)
        # For non-arrow functions called as methods, bind `this`; arrows keep
        # their captured this (set at closure creation).
        frame_this = callee.this if fn.is_arrow else this
        frame = CallFrame(callee, base, frame_this)
        self.frames.append(frame)

    # -- dispatch loop --
    def _dispatch(self, stop_at_depth=0):
        while len(self.frames) > stop_at_depth:
            frame = self.frames[-1]
            code = frame.code
            instructions = code.code
            ip = frame.ip
            if ip >= len(instructions):
                self.frames.pop()
                continue
            ins = instructions[ip]
            frame.ip = ip + 1
            op = ins.op
            operand = ins.operand

            if op == Op.LOAD_CONST:
                self._push(code.constants[operand])
            elif op == Op.LOAD_TRUE:
                self._push(True)
            elif op == Op.LOAD_FALSE:
                self._push(False)
            elif op == Op.LOAD_NULL:
                self._push(NULL)
            elif op == Op.LOAD_UNDEFINED:
                self._push(UNDEFINED)

            elif op == Op.LOAD_LOCAL:
                self._push(self.stack[frame.base + operand])
            elif op == Op.STORE_LOCAL:
                self.stack[frame.base + operand] = self._peek()
            elif op == Op.DEFINE_GLOBAL:
                name = code.constants[operand]
                value = self._pop()
                is_const = name in self._const_globals
                self.env.define(name, value, is_const=is_const)
            elif op == Op.LOAD_GLOBAL:
                name = code.constants[operand]
                if not self.env.has(name):
                    raise PyJSRuntimeError(f"{name} is not defined", ins.line)
                self._push(self.env.get(name))
            elif op == Op.STORE_GLOBAL:
                name = code.constants[operand]
                try:
                    self.env.assign(name, self._peek())
                except PyJSRuntimeError as e:
                    raise PyJSRuntimeError(e.message, ins.line)

            elif op == Op.LOAD_UPVALUE:
                self._push(frame.closure.upvalues[operand].get())
            elif op == Op.STORE_UPVALUE:
                frame.closure.upvalues[operand].set(self._peek())
            elif op == Op.CLOSE_UPVALUE:
                # Close the open upvalue for this local slot (if captured).
                self._close_upvalues_from(frame.base + operand)

            elif op == Op.ADD:
                b = self._pop(); a = self._pop(); self._push(js_add(a, b))
            elif op == Op.SUB:
                b = self._pop(); a = self._pop()
                self._push(to_number(a) - to_number(b))
            elif op == Op.MUL:
                b = self._pop(); a = self._pop()
                self._push(to_number(a) * to_number(b))
            elif op == Op.DIV:
                b = self._pop(); a = self._pop()
                self._push(self._divide(a, b))
            elif op == Op.MOD:
                b = self._pop(); a = self._pop()
                self._push(self._modulo(a, b))
            elif op == Op.POW:
                b = self._pop(); a = self._pop()
                self._push(self._power(a, b))
            elif op == Op.NEG:
                self._push(-to_number(self._pop()))

            elif op == Op.EQ:
                b = self._pop(); a = self._pop()
                self._push(js_loose_equals(a, b))
            elif op == Op.NEQ:
                b = self._pop(); a = self._pop()
                self._push(not js_loose_equals(a, b))
            elif op == Op.STRICT_EQ:
                b = self._pop(); a = self._pop()
                self._push(js_strict_equals(a, b))
            elif op == Op.STRICT_NEQ:
                b = self._pop(); a = self._pop()
                self._push(not js_strict_equals(a, b))
            elif op == Op.GT:
                b = self._pop(); a = self._pop()
                self._push(js_compare(a, b, ">"))
            elif op == Op.LT:
                b = self._pop(); a = self._pop()
                self._push(js_compare(a, b, "<"))
            elif op == Op.GTE:
                b = self._pop(); a = self._pop()
                self._push(js_compare(a, b, ">="))
            elif op == Op.LTE:
                b = self._pop(); a = self._pop()
                self._push(js_compare(a, b, "<="))

            elif op == Op.NOT:
                self._push(not is_truthy(self._pop()))
            elif op == Op.TYPEOF:
                self._push(js_typeof(self._pop()))
            elif op == Op.LOAD_THIS:
                self._push(frame.this)

            elif op == Op.JUMP:
                frame.ip = operand
            elif op == Op.JUMP_IF_FALSE:
                cond = self._pop()
                if not is_truthy(cond):
                    frame.ip = operand
            elif op == Op.JUMP_IF_TRUE:
                cond = self._pop()
                if is_truthy(cond):
                    frame.ip = operand
            elif op == Op.JUMP_IF_FALSE_KEEP:
                if not is_truthy(self._peek()):
                    frame.ip = operand
            elif op == Op.JUMP_IF_TRUE_KEEP:
                if is_truthy(self._peek()):
                    frame.ip = operand
            elif op == Op.POP:
                self.last_value = self._pop()
            elif op == Op.DUP:
                self._push(self._peek())

            elif op == Op.MAKE_CLOSURE:
                self._make_closure(code, frame, operand)
            elif op == Op.CALL:
                self._invoke(self._callee_at(operand), operand)
            elif op == Op.CALL_METHOD:
                self._call_method(operand)
            elif op == Op.CALL_SPREAD:
                self._call_spread(operand)

            elif op == Op.BUILD_ARRAY:
                n = operand
                items = self.stack[len(self.stack) - n:]
                del self.stack[len(self.stack) - n:]
                self._push(JSArray(items))
            elif op == Op.BUILD_ARRAY_SPREAD:
                self._build_array_spread(operand)
            elif op == Op.BUILD_OBJECT:
                self._build_object(operand)
            elif op == Op.GET_INDEX:
                key = self._pop(); obj = self._pop()
                self._push(get_member(obj, key))
            elif op == Op.SET_INDEX:
                value = self._pop(); key = self._pop(); obj = self._pop()
                self._push(set_member(obj, key, value))
            elif op == Op.GET_PROP:
                name = code.constants[operand]
                obj = self._pop()
                self._push(get_member(obj, name))
            elif op == Op.SET_PROP:
                name = code.constants[operand]
                value = self._pop(); obj = self._pop()
                self._push(set_member(obj, name, value))
            elif op == Op.SPREAD:
                # Mark the top-of-stack array as a spread segment by wrapping it
                # in a sentinel; consumed by BUILD_ARRAY_SPREAD / CALL_SPREAD.
                self._push(_Spread(self._pop()))

            elif op == Op.RETURN:
                if self._do_return(frame):
                    # Returned from the top-level invoked frame requested by
                    # call_value; hand control back to caller.
                    if len(self.frames) <= stop_at_depth:
                        return

            elif op == Op.HALT:
                self.frames.pop()
                return

            else:
                raise PyJSRuntimeError(
                    f"Unsupported opcode {op.name} in this phase", ins.line)

    # -- function helpers --
    def _callee_at(self, argc):
        # callee sits below this + args: index = top - argc - 2
        return self.stack[len(self.stack) - argc - 2]

    def _call_method(self, argc):
        # Stack: [receiver, method, args...]
        top = len(self.stack)
        receiver = self.stack[top - argc - 2]
        method = self.stack[top - argc - 1]
        # Re-arrange into the CALL protocol [callee, this, args...]:
        # overwrite receiver slot with method, method slot with receiver.
        self.stack[top - argc - 2] = method
        self.stack[top - argc - 1] = receiver
        self._invoke(method, argc, this=receiver)

    def _flatten_spread_segment(self, value):
        if isinstance(value, _Spread):
            inner = value.value
            if isinstance(inner, JSArray):
                return list(inner.items)
            if isinstance(inner, str):
                return list(inner)
            raise PyJSRuntimeError("spread element is not iterable")
        return [value]

    def _build_array_spread(self, n):
        segments = self.stack[len(self.stack) - n:]
        del self.stack[len(self.stack) - n:]
        out = []
        for seg in segments:
            out.extend(self._flatten_spread_segment(seg))
        self._push(JSArray(out))

    def _build_object(self, n):
        # Stack holds n (key, value) pairs in order.
        pairs = self.stack[len(self.stack) - 2 * n:]
        del self.stack[len(self.stack) - 2 * n:]
        obj = JSObject()
        for i in range(n):
            key = pairs[2 * i]
            val = pairs[2 * i + 1]
            obj.set(key if isinstance(key, str) else _key_to_str(key), val)
        self._push(obj)

    def _call_spread(self, mode):
        # mode 0: plain call  [callee, this, argsArray]
        # mode 1: method call [receiver, method, argsArray]
        args_array = self._pop()
        args = list(args_array.items) if isinstance(args_array, JSArray) else []
        if mode == 1:
            method = self._pop(); receiver = self._pop()
            callee = method
            this = receiver
        else:
            self._pop()                 # this placeholder (undefined)
            callee = self._pop()
            this = UNDEFINED
        # push under the call protocol then invoke
        self._push(callee)
        self._push(this)
        for a in args:
            self._push(a)
        self._invoke(callee, len(args), this=this)

    def _make_closure(self, code, frame, const_idx):
        fn = code.constants[const_idx]
        upvalues = []
        for (is_local, index) in fn.code.upvalues:
            if is_local:
                # Capture from the current frame's locals (open upvalue).
                upvalues.append(self._capture_upvalue(frame.base + index))
            else:
                # Inherit an already-captured upvalue from the enclosing
                # closure.
                upvalues.append(frame.closure.upvalues[index])
        self._push(JSClosure(fn, upvalues, this=frame.this if fn.is_arrow else UNDEFINED))

    def _do_return(self, frame):
        result = self._pop()
        # Close any upvalues that point into this frame's window before we
        # discard it, so closures created here keep working.
        self._close_upvalues_from(frame.base)
        self.frames.pop()
        # Drop the entire call window: callee (base-2), this (base-1), args and
        # locals (base ..). Then push the result for the caller.
        del self.stack[frame.base - 2:]
        self._push(result)
        return True

    # -- arithmetic edge cases --
    def _divide(self, a, b):
        na, nb = to_number(a), to_number(b)
        if nb == 0.0:
            if na == 0.0 or na != na:
                return float("nan")
            return float("inf") if na > 0 else float("-inf")
        return na / nb

    def _modulo(self, a, b):
        na, nb = to_number(a), to_number(b)
        if nb == 0.0 or na != na or nb != nb:
            return float("nan")
        import math
        return math.fmod(na, nb)

    def _power(self, a, b):
        na, nb = to_number(a), to_number(b)
        try:
            return float(na ** nb)
        except (ValueError, OverflowError):
            return float("nan")


def interpret(source, environment=None):
    """Lex + parse + compile + run a source string. Returns the VM instance so
    callers can inspect globals / last value."""
    from ..compiler.compiler import compile_source
    code = compile_source(source)
    vm = VM(environment=environment)
    vm.run(code)
    return vm
