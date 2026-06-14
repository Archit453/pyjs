"""Member access + method dispatch for PyJS runtime values.

The compiler emits GET_PROP / GET_INDEX / SET_PROP / SET_INDEX; the VM defers
to get_member / set_member here so all property/coercion logic stays in the
runtime layer (architecture: nothing outside runtime implements semantics).

String and array methods are exposed as bound NativeFunctionValues. Higher-order
methods (map/filter/reduce/...) re-enter the VM via vm.call_value, reusing the
Phase 5 function/closure machinery.
"""
from .values import (
    UNDEFINED, NULL, JSObject, JSArray, NativeFunctionValue,
    to_js_string, to_number, is_truthy, js_strict_equals,
)
from .environment import PyJSRuntimeError


def _native(name, fn):
    return NativeFunctionValue(name, fn)


# ---------------------------------------------------------------------------
# Index normalization helpers
# ---------------------------------------------------------------------------

def _to_index(value):
    """Coerce an index value to an int (JS array index). Returns None if the
    key is not an array-index (e.g. a string property like 'length')."""
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        if value == int(value):
            return int(value)
        return None
    if isinstance(value, str):
        try:
            f = float(value)
        except ValueError:
            return None
        if f == int(f):
            return int(f)
        return None
    return None


def _norm_slice(start, end, length):
    """Normalize JS slice(start, end) bounds."""
    if start is None:
        start = 0
    else:
        start = int(start)
        if start < 0:
            start = max(length + start, 0)
        else:
            start = min(start, length)
    if end is None:
        end = length
    else:
        end = int(end)
        if end < 0:
            end = max(length + end, 0)
        else:
            end = min(end, length)
    if end < start:
        end = start
    return start, end


# ---------------------------------------------------------------------------
# String methods
# ---------------------------------------------------------------------------

def _arg(args, i, default=UNDEFINED):
    return args[i] if i < len(args) else default


def _string_method(s, name):
    if name == "length":
        return float(len(s))

    def replace(vm, this, args):
        target = to_js_string(_arg(args, 0))
        repl = to_js_string(_arg(args, 1))
        return s.replace(target, repl, 1)

    def replace_all(vm, this, args):
        target = to_js_string(_arg(args, 0))
        repl = to_js_string(_arg(args, 1))
        return s.replace(target, repl)

    def substring(vm, this, args):
        a = _arg(args, 0)
        b = _arg(args, 1)
        start = 0 if a is UNDEFINED else max(0, int(to_number(a)))
        end = len(s) if b is UNDEFINED else max(0, int(to_number(b)))
        start = min(start, len(s)); end = min(end, len(s))
        if start > end:
            start, end = end, start
        return s[start:end]

    def slice_(vm, this, args):
        a = _arg(args, 0)
        b = _arg(args, 1)
        start = None if a is UNDEFINED else int(to_number(a))
        end = None if b is UNDEFINED else int(to_number(b))
        st, en = _norm_slice(start, end, len(s))
        return s[st:en]

    def split(vm, this, args):
        sep = _arg(args, 0)
        if sep is UNDEFINED:
            return JSArray([s])
        sep = to_js_string(sep)
        if sep == "":
            return JSArray(list(s))
        return JSArray(s.split(sep))

    def trim(vm, this, args):
        return s.strip()

    def to_upper(vm, this, args):
        return s.upper()

    def to_lower(vm, this, args):
        return s.lower()

    def includes(vm, this, args):
        return to_js_string(_arg(args, 0)) in s

    def starts_with(vm, this, args):
        return s.startswith(to_js_string(_arg(args, 0)))

    def ends_with(vm, this, args):
        return s.endswith(to_js_string(_arg(args, 0)))

    def index_of(vm, this, args):
        return float(s.find(to_js_string(_arg(args, 0))))

    def char_at(vm, this, args):
        i = int(to_number(_arg(args, 0)))
        return s[i] if 0 <= i < len(s) else ""

    table = {
        "replace": replace, "replaceAll": replace_all, "substring": substring,
        "slice": slice_, "split": split, "trim": trim,
        "toUpperCase": to_upper, "toLowerCase": to_lower,
        "includes": includes, "startsWith": starts_with,
        "endsWith": ends_with, "indexOf": index_of, "charAt": char_at,
    }
    fn = table.get(name)
    if fn is None:
        return UNDEFINED
    return _native("String.prototype." + name, fn)


# ---------------------------------------------------------------------------
# Array methods
# ---------------------------------------------------------------------------

def _array_method(arr, name):
    items = arr.items

    if name == "length":
        return float(len(items))

    def push(vm, this, args):
        for a in args:
            items.append(a)
        return float(len(items))

    def pop(vm, this, args):
        return items.pop() if items else UNDEFINED

    def shift(vm, this, args):
        return items.pop(0) if items else UNDEFINED

    def unshift(vm, this, args):
        for i, a in enumerate(args):
            items.insert(i, a)
        return float(len(items))

    def slice_(vm, this, args):
        a = _arg(args, 0); b = _arg(args, 1)
        start = None if a is UNDEFINED else int(to_number(a))
        end = None if b is UNDEFINED else int(to_number(b))
        st, en = _norm_slice(start, end, len(items))
        return JSArray(items[st:en])

    def splice(vm, this, args):
        start = int(to_number(_arg(args, 0, 0.0)))
        if start < 0:
            start = max(len(items) + start, 0)
        else:
            start = min(start, len(items))
        if len(args) < 2:
            delete_count = len(items) - start
        else:
            delete_count = max(0, min(int(to_number(args[1])), len(items) - start))
        removed = items[start:start + delete_count]
        new_items = list(args[2:])
        items[start:start + delete_count] = new_items
        return JSArray(removed)

    def concat(vm, this, args):
        out = list(items)
        for a in args:
            if isinstance(a, JSArray):
                out.extend(a.items)
            else:
                out.append(a)
        return JSArray(out)

    def includes(vm, this, args):
        target = _arg(args, 0)
        return any(js_strict_equals(x, target) for x in items)

    def index_of(vm, this, args):
        target = _arg(args, 0)
        for i, x in enumerate(items):
            if js_strict_equals(x, target):
                return float(i)
        return -1.0

    def reverse(vm, this, args):
        items.reverse()
        return arr

    def sort(vm, this, args):
        comparator = _arg(args, 0)
        if comparator is UNDEFINED:
            items.sort(key=to_js_string)
        else:
            import functools

            def cmp(a, b):
                r = to_number(vm.call_value(comparator, [a, b]))
                if r != r:
                    return 0
                return -1 if r < 0 else (1 if r > 0 else 0)

            items.sort(key=functools.cmp_to_key(cmp))
        return arr

    # -- higher-order --
    def map_(vm, this, args):
        fn = _arg(args, 0)
        out = []
        for i, x in enumerate(items):
            out.append(vm.call_value(fn, [x, float(i), arr]))
        return JSArray(out)

    def filter_(vm, this, args):
        fn = _arg(args, 0)
        out = []
        for i, x in enumerate(items):
            if is_truthy(vm.call_value(fn, [x, float(i), arr])):
                out.append(x)
        return JSArray(out)

    def reduce_(vm, this, args):
        fn = _arg(args, 0)
        has_init = len(args) >= 2
        idx = 0
        if has_init:
            acc = args[1]
        else:
            if not items:
                raise PyJSRuntimeError(
                    "Reduce of empty array with no initial value")
            acc = items[0]
            idx = 1
        while idx < len(items):
            acc = vm.call_value(fn, [acc, items[idx], float(idx), arr])
            idx += 1
        return acc

    def find_(vm, this, args):
        fn = _arg(args, 0)
        for i, x in enumerate(items):
            if is_truthy(vm.call_value(fn, [x, float(i), arr])):
                return x
        return UNDEFINED

    def some_(vm, this, args):
        fn = _arg(args, 0)
        for i, x in enumerate(items):
            if is_truthy(vm.call_value(fn, [x, float(i), arr])):
                return True
        return False

    def every_(vm, this, args):
        fn = _arg(args, 0)
        for i, x in enumerate(items):
            if not is_truthy(vm.call_value(fn, [x, float(i), arr])):
                return False
        return True

    def for_each(vm, this, args):
        fn = _arg(args, 0)
        for i, x in enumerate(items):
            vm.call_value(fn, [x, float(i), arr])
        return UNDEFINED

    def join(vm, this, args):
        sep = _arg(args, 0)
        sep = "," if sep is UNDEFINED else to_js_string(sep)
        return sep.join("" if (x is UNDEFINED or x is NULL) else to_js_string(x)
                        for x in items)

    table = {
        "push": push, "pop": pop, "shift": shift, "unshift": unshift,
        "slice": slice_, "splice": splice, "concat": concat,
        "includes": includes, "indexOf": index_of, "reverse": reverse,
        "sort": sort, "map": map_, "filter": filter_, "reduce": reduce_,
        "find": find_, "some": some_, "every": every_, "forEach": for_each,
        "join": join,
    }
    fn = table.get(name)
    if fn is None:
        return UNDEFINED
    return _native("Array.prototype." + name, fn)


# ---------------------------------------------------------------------------
# Public get/set member
# ---------------------------------------------------------------------------

def get_member(obj, key):
    """Property/index access. `key` is the runtime key value (str or number)."""
    if isinstance(obj, JSArray):
        idx = _to_index(key)
        if idx is not None:
            return obj.get_index(idx)
        return _array_method(obj, to_js_string(key))
    if isinstance(obj, str):
        idx = _to_index(key)
        if idx is not None:
            return obj[idx] if 0 <= idx < len(obj) else UNDEFINED
        return _string_method(obj, to_js_string(key))
    if isinstance(obj, JSObject):
        return obj.get(to_js_string(key))
    if obj is UNDEFINED or obj is NULL:
        raise PyJSRuntimeError(
            f"Cannot read properties of {to_js_string(obj)} "
            f"(reading '{to_js_string(key)}')")
    if isinstance(obj, float):
        return UNDEFINED
    return UNDEFINED


def set_member(obj, key, value):
    """Property/index assignment. Returns the assigned value."""
    if isinstance(obj, JSArray):
        idx = _to_index(key)
        if idx is not None:
            obj.set_index(idx, value)
            return value
        # non-index assignment on arrays is ignored (length etc.)
        return value
    if isinstance(obj, JSObject):
        obj.set(to_js_string(key), value)
        return value
    if obj is UNDEFINED or obj is NULL:
        raise PyJSRuntimeError(
            f"Cannot set properties of {to_js_string(obj)} "
            f"(setting '{to_js_string(key)}')")
    return value
