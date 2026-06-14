"""Runtime value model and JS coercion rules for PyJS.

Primitives use native Python types:
    number  -> float
    string  -> str
    boolean -> bool
    null    -> JSNull (singleton)
    undefined -> JSUndefined (singleton)

Reference types get dedicated classes: JSObject, JSArray, JSFunction,
JSClosure, Upvalue, NativeFunctionValue.

ALL coercion logic lives here (is_truthy, to_number, to_js_string, ==, ===,
typeof). Nothing outside this module should implement coercion.

Important: `bool` is a subclass of `int` in Python, so every type check that
distinguishes numbers from booleans MUST test `bool` before `float`/`int`.
"""


class _Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


class JSUndefined(_Singleton):
    def __repr__(self):
        return "undefined"

    def __bool__(self):
        return False


class JSNull(_Singleton):
    def __repr__(self):
        return "null"

    def __bool__(self):
        return False


UNDEFINED = JSUndefined()
NULL = JSNull()


class JSObject:
    """Plain JS object: insertion-ordered string-keyed property map."""

    __slots__ = ("props",)

    def __init__(self, props=None):
        self.props = {}
        if props:
            for k, v in props.items():
                self.props[str(k)] = v

    def get(self, key):
        return self.props.get(str(key), UNDEFINED)

    def set(self, key, value):
        self.props[str(key)] = value

    def has(self, key):
        return str(key) in self.props

    def delete(self, key):
        self.props.pop(str(key), None)

    def __repr__(self):
        return js_repr(self)


class JSArray:
    """JS array. Has-a Python list (`items`); never subclasses list."""

    __slots__ = ("items",)

    def __init__(self, items=None):
        self.items = list(items) if items is not None else []

    @property
    def length(self):
        return float(len(self.items))

    def get_index(self, i):
        if 0 <= i < len(self.items):
            return self.items[i]
        return UNDEFINED

    def set_index(self, i, value):
        if i < 0:
            return
        while len(self.items) <= i:
            self.items.append(UNDEFINED)
        self.items[i] = value

    def __repr__(self):
        return js_repr(self)


class JSFunction:
    """Immutable compiled function template: code + upvalue descriptors.

    Multiple JSClosures can share one JSFunction. `is_arrow` controls whether
    the function receives its own `this` (false for arrows -> captured).
    """

    __slots__ = ("code", "name", "is_arrow")

    def __init__(self, code_object, is_arrow=False):
        self.code = code_object
        self.name = code_object.name
        self.is_arrow = is_arrow

    def __repr__(self):
        return f"<function {self.name}>"


class Upvalue:
    """Reference to a captured variable.

    Open: `location` indexes the VM value stack via `stack`.
    Closed: value copied to `closed` (so it survives the owning frame).
    """

    __slots__ = ("stack", "location", "closed", "is_closed")

    def __init__(self, stack, location):
        self.stack = stack
        self.location = location
        self.closed = None
        self.is_closed = False

    def get(self):
        return self.closed if self.is_closed else self.stack[self.location]

    def set(self, value):
        if self.is_closed:
            self.closed = value
        else:
            self.stack[self.location] = value

    def close(self):
        self.closed = self.stack[self.location]
        self.is_closed = True
        self.stack = None


class JSClosure:
    """Runtime function instance: JSFunction + captured upvalues + bound this."""

    __slots__ = ("function", "upvalues", "this")

    def __init__(self, function, upvalues=None, this=UNDEFINED):
        self.function = function
        self.upvalues = upvalues if upvalues is not None else []
        self.this = this

    @property
    def name(self):
        return self.function.name

    def __repr__(self):
        return f"<closure {self.name}>"


class NativeFunctionValue:
    """Native function implemented in Python.

    Signature: fn(vm, this, args) -> value
    `vm` lets higher-order natives re-enter the interpreter via vm.call_value.
    """

    __slots__ = ("name", "fn")

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn

    def __repr__(self):
        return f"<native {self.name}>"


def is_callable(v):
    return isinstance(v, (JSClosure, NativeFunctionValue))


# ---------------------------------------------------------------------------
# Coercions / display (JS semantics) -- the ONLY place these rules live.
# ---------------------------------------------------------------------------

def is_truthy(v):
    if v is UNDEFINED or v is NULL:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        return v != 0.0 and v == v  # NaN -> False
    if isinstance(v, str):
        return len(v) > 0
    return True


def to_number(v):
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, float):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return float("nan")
    if v is NULL:
        return 0.0
    if v is UNDEFINED:
        return float("nan")
    if isinstance(v, JSArray):
        if len(v.items) == 0:
            return 0.0
        if len(v.items) == 1:
            return to_number(v.items[0])
        return float("nan")
    return float("nan")


def _fmt_number(n):
    if n != n:
        return "NaN"
    if n == float("inf"):
        return "Infinity"
    if n == float("-inf"):
        return "-Infinity"
    if n == int(n):
        return str(int(n))
    return repr(n)


def to_js_string(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return _fmt_number(v)
    if isinstance(v, str):
        return v
    if v is UNDEFINED:
        return "undefined"
    if v is NULL:
        return "null"
    if isinstance(v, JSArray):
        return ",".join("" if (x is UNDEFINED or x is NULL) else to_js_string(x)
                        for x in v.items)
    if isinstance(v, JSObject):
        return "[object Object]"
    if isinstance(v, (JSClosure, JSFunction, NativeFunctionValue)):
        return f"function {getattr(v, 'name', '')}() {{ [native code] }}"
    return str(v)


def js_repr(v):
    """console.log top-level representation (bare strings, quoted when nested)."""
    if isinstance(v, str):
        return v
    return _inspect(v)


def _inspect(v):
    if isinstance(v, str):
        return f"'{v}'"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return _fmt_number(v)
    if v is UNDEFINED:
        return "undefined"
    if v is NULL:
        return "null"
    if isinstance(v, JSArray):
        if not v.items:
            return "[]"
        return "[ " + ", ".join(_inspect(x) for x in v.items) + " ]"
    if isinstance(v, JSObject):
        if not v.props:
            return "{}"
        inner = ", ".join(f"{k}: {_inspect(val)}" for k, val in v.props.items())
        return "{ " + inner + " }"
    return to_js_string(v)


def js_typeof(v):
    if v is UNDEFINED:
        return "undefined"
    if v is NULL:
        return "object"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, (JSClosure, JSFunction, NativeFunctionValue)):
        return "function"
    return "object"


def js_loose_equals(a, b):
    """Loose equality (==)."""
    ta_bool, tb_bool = isinstance(a, bool), isinstance(b, bool)
    # Same primitive class fast paths.
    if ta_bool and tb_bool:
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if (isinstance(a, float) and not ta_bool) and (isinstance(b, float) and not tb_bool):
        if a != a or b != b:
            return False
        return a == b
    if a is NULL and b is NULL:
        return True
    if a is UNDEFINED and b is UNDEFINED:
        return True
    if (a is NULL and b is UNDEFINED) or (a is UNDEFINED and b is NULL):
        return True
    if a is NULL or a is UNDEFINED or b is NULL or b is UNDEFINED:
        return False
    # number/boolean/string mixed -> compare as numbers
    if isinstance(a, (float, bool, str)) and isinstance(b, (float, bool, str)):
        na, nb = to_number(a), to_number(b)
        if na != na or nb != nb:
            return False
        return na == nb
    # reference types -> identity
    return a is b


def js_strict_equals(a, b):
    """Strict equality (===)."""
    ta_bool, tb_bool = isinstance(a, bool), isinstance(b, bool)
    if ta_bool or tb_bool:
        return ta_bool and tb_bool and a == b
    if isinstance(a, float) and isinstance(b, float):
        if a != a or b != b:
            return False
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    if a is NULL and b is NULL:
        return True
    if a is UNDEFINED and b is UNDEFINED:
        return True
    if isinstance(a, (JSObject, JSArray, JSClosure, JSFunction, NativeFunctionValue)):
        return a is b
    return False


def js_compare(a, b, op):
    """Relational comparison (>, <, >=, <=). String vs string compares
    lexicographically; otherwise numeric coercion (JS abstract relational)."""
    if isinstance(a, str) and isinstance(b, str):
        if op == ">":
            return a > b
        if op == "<":
            return a < b
        if op == ">=":
            return a >= b
        return a <= b
    na, nb = to_number(a), to_number(b)
    if na != na or nb != nb:
        return False
    if op == ">":
        return na > nb
    if op == "<":
        return na < nb
    if op == ">=":
        return na >= nb
    return na <= nb


def js_add(a, b):
    """JS `+`: string concat if either operand is a string, else numeric add."""
    if isinstance(a, str) or isinstance(b, str):
        return to_js_string(a) + to_js_string(b)
    return to_number(a) + to_number(b)
