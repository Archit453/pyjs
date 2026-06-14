"""AST node definitions for PyJS.

Nodes are lightweight data classes (no behavior). They form the contract
between the parser (Phase 3) and the compiler (Phase 4). Field names are
stable; the compiler depends on them.

Every node carries an optional source `line` for diagnostics.
"""


class Node:
    _fields = ()
    line = 0

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return all(getattr(self, f) == getattr(other, f) for f in self._fields)

    def __repr__(self):
        vals = ", ".join(f"{f}={getattr(self, f)!r}" for f in self._fields)
        return f"{type(self).__name__}({vals})"


# ---------------------------------------------------------------------------
# Program & statements
# ---------------------------------------------------------------------------

class Program(Node):
    _fields = ("body",)

    def __init__(self, body):
        self.body = body


class VarDecl(Node):
    _fields = ("kind", "name", "init")

    def __init__(self, kind, name, init, line=0):
        self.kind = kind        # 'let' | 'const'
        self.name = name        # str
        self.init = init        # expr | None
        self.line = line


class FunctionDecl(Node):
    _fields = ("name", "params", "rest", "body")

    def __init__(self, name, params, rest, body, line=0):
        self.name = name        # str
        self.params = params    # list[str]
        self.rest = rest        # str | None
        self.body = body        # list[Node]
        self.line = line


class ReturnStmt(Node):
    _fields = ("value",)

    def __init__(self, value, line=0):
        self.value = value      # expr | None
        self.line = line


class IfStmt(Node):
    _fields = ("test", "consequent", "alternate")

    def __init__(self, test, consequent, alternate, line=0):
        self.test = test
        self.consequent = consequent
        self.alternate = alternate   # Node | None (may be another IfStmt)
        self.line = line


class WhileStmt(Node):
    _fields = ("test", "body")

    def __init__(self, test, body, line=0):
        self.test = test
        self.body = body
        self.line = line


class DoWhileStmt(Node):
    _fields = ("body", "test")

    def __init__(self, body, test, line=0):
        self.body = body
        self.test = test
        self.line = line


class ForStmt(Node):
    _fields = ("init", "test", "update", "body")

    def __init__(self, init, test, update, body, line=0):
        self.init = init        # VarDecl | ExpressionStmt | None
        self.test = test        # expr | None
        self.update = update    # expr | None
        self.body = body
        self.line = line


class SwitchCase(Node):
    _fields = ("test", "body")

    def __init__(self, test, body, line=0):
        self.test = test        # expr | None (None == default)
        self.body = body        # list[Node]
        self.line = line


class SwitchStmt(Node):
    _fields = ("discriminant", "cases")

    def __init__(self, discriminant, cases, line=0):
        self.discriminant = discriminant
        self.cases = cases      # list[SwitchCase]
        self.line = line


class BreakStmt(Node):
    _fields = ()

    def __init__(self, line=0):
        self.line = line


class ContinueStmt(Node):
    _fields = ()

    def __init__(self, line=0):
        self.line = line


class Block(Node):
    _fields = ("body",)

    def __init__(self, body, line=0):
        self.body = body        # list[Node]
        self.line = line


class ExpressionStmt(Node):
    _fields = ("expr",)

    def __init__(self, expr, line=0):
        self.expr = expr
        self.line = line


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

class NumberLiteral(Node):
    _fields = ("value",)

    def __init__(self, value, line=0):
        self.value = value      # float
        self.line = line


class StringLiteral(Node):
    _fields = ("value",)

    def __init__(self, value, line=0):
        self.value = value      # str
        self.line = line


class BooleanLiteral(Node):
    _fields = ("value",)

    def __init__(self, value, line=0):
        self.value = value      # bool
        self.line = line


class NullLiteral(Node):
    _fields = ()

    def __init__(self, line=0):
        self.line = line


class UndefinedLiteral(Node):
    _fields = ()

    def __init__(self, line=0):
        self.line = line


class Identifier(Node):
    _fields = ("name",)

    def __init__(self, name, line=0):
        self.name = name
        self.line = line


class ArrayLiteral(Node):
    _fields = ("elements",)

    def __init__(self, elements, line=0):
        self.elements = elements   # list[expr | SpreadElement]
        self.line = line


class Property(Node):
    _fields = ("key", "value", "computed")

    def __init__(self, key, value, computed, line=0):
        # key: str (static) or expr (computed)
        self.key = key
        self.value = value
        self.computed = computed
        self.line = line


class ObjectLiteral(Node):
    _fields = ("properties",)

    def __init__(self, properties, line=0):
        self.properties = properties   # list[Property]
        self.line = line


class SpreadElement(Node):
    _fields = ("argument",)

    def __init__(self, argument, line=0):
        self.argument = argument
        self.line = line


class FunctionExpr(Node):
    _fields = ("name", "params", "rest", "body", "is_arrow")

    def __init__(self, name, params, rest, body, is_arrow=False, line=0):
        self.name = name        # str | None
        self.params = params
        self.rest = rest
        self.body = body        # list[Node]
        self.is_arrow = is_arrow
        self.line = line


# ---------------------------------------------------------------------------
# Operator expressions
# ---------------------------------------------------------------------------

class UnaryExpr(Node):
    _fields = ("op", "operand")

    def __init__(self, op, operand, line=0):
        self.op = op
        self.operand = operand
        self.line = line


class UpdateExpr(Node):
    _fields = ("op", "target", "prefix")

    def __init__(self, op, target, prefix, line=0):
        self.op = op            # '++' | '--'
        self.target = target
        self.prefix = prefix    # bool
        self.line = line


class BinaryExpr(Node):
    _fields = ("op", "left", "right")

    def __init__(self, op, left, right, line=0):
        self.op = op
        self.left = left
        self.right = right
        self.line = line


class LogicalExpr(Node):
    _fields = ("op", "left", "right")

    def __init__(self, op, left, right, line=0):
        self.op = op            # '&&' | '||'
        self.left = left
        self.right = right
        self.line = line


class AssignExpr(Node):
    _fields = ("op", "target", "value")

    def __init__(self, op, target, value, line=0):
        self.op = op            # '=' | '+=' | '-='
        self.target = target    # Identifier | MemberExpr
        self.value = value
        self.line = line


class ConditionalExpr(Node):
    _fields = ("test", "consequent", "alternate")

    def __init__(self, test, consequent, alternate, line=0):
        self.test = test
        self.consequent = consequent
        self.alternate = alternate
        self.line = line


class CallExpr(Node):
    _fields = ("callee", "args")

    def __init__(self, callee, args, line=0):
        self.callee = callee
        self.args = args        # list[expr | SpreadElement]
        self.line = line


class MemberExpr(Node):
    _fields = ("obj", "prop", "computed")

    def __init__(self, obj, prop, computed, line=0):
        self.obj = obj
        self.prop = prop        # str (static) | expr (computed)
        self.computed = computed
        self.line = line
