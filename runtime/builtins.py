"""Global builtins for PyJS: console, Math, Date.

Installed into an Environment as global bindings. Native functions follow the
Phase 5 signature fn(vm, this, args) -> value so they can be invoked through
the same CALL machinery.
"""
import math as _math
import random as _random
import time as _time

from .values import (
    UNDEFINED, JSObject, JSArray, NativeFunctionValue,
    to_js_string, to_number, js_repr,
)


def _native(name, fn):
    return NativeFunctionValue(name, fn)


def _nums(args):
    return [to_number(a) for a in args]


def make_console():
    obj = JSObject()

    def log(vm, this, args):
        line = " ".join(js_repr(a) for a in args)
        # Record output on the VM so tests can assert without capturing stdout,
        # and still echo to stdout for real use.
        out = getattr(vm, "console_output", None)
        if out is not None:
            out.append(line)
        print(line)
        return UNDEFINED

    obj.set("log", _native("console.log", log))
    obj.set("error", _native("console.error", log))
    obj.set("warn", _native("console.warn", log))
    return obj


def make_math():
    obj = JSObject()
    obj.set("PI", float(_math.pi))
    obj.set("E", float(_math.e))

    def _unary(fnname, pyfn):
        def f(vm, this, args):
            return float(pyfn(to_number(args[0]) if args else float("nan")))
        return _native("Math." + fnname, f)

    def _abs(vm, this, args):
        return float(abs(to_number(args[0]))) if args else float("nan")

    def _floor(vm, this, args):
        n = to_number(args[0]) if args else float("nan")
        return float(_math.floor(n)) if n == n else float("nan")

    def _ceil(vm, this, args):
        n = to_number(args[0]) if args else float("nan")
        return float(_math.ceil(n)) if n == n else float("nan")

    def _round(vm, this, args):
        n = to_number(args[0]) if args else float("nan")
        if n != n:
            return float("nan")
        # JS Math.round: round half up (toward +Infinity).
        return float(_math.floor(n + 0.5))

    def _max(vm, this, args):
        if not args:
            return float("-inf")
        ns = _nums(args)
        if any(n != n for n in ns):
            return float("nan")
        return float(max(ns))

    def _min(vm, this, args):
        if not args:
            return float("inf")
        ns = _nums(args)
        if any(n != n for n in ns):
            return float("nan")
        return float(min(ns))

    def _random_fn(vm, this, args):
        return float(_random.random())

    def _sqrt(vm, this, args):
        n = to_number(args[0]) if args else float("nan")
        if n < 0 or n != n:
            return float("nan")
        return float(_math.sqrt(n))

    def _pow(vm, this, args):
        b = to_number(args[0]) if len(args) > 0 else float("nan")
        e = to_number(args[1]) if len(args) > 1 else float("nan")
        try:
            return float(b ** e)
        except (ValueError, OverflowError):
            return float("nan")

    obj.set("abs", _native("Math.abs", _abs))
    obj.set("floor", _native("Math.floor", _floor))
    obj.set("ceil", _native("Math.ceil", _ceil))
    obj.set("round", _native("Math.round", _round))
    obj.set("max", _native("Math.max", _max))
    obj.set("min", _native("Math.min", _min))
    obj.set("random", _native("Math.random", _random_fn))
    obj.set("sqrt", _native("Math.sqrt", _sqrt))
    obj.set("pow", _native("Math.pow", _pow))
    return obj


def make_date_constructor():
    """Date() returns a JSObject with getTime(). Date.now() also provided.

    Simplified: a Date instance captures epoch milliseconds at creation.
    """
    def construct(vm, this, args):
        d = JSObject()
        if args:
            ms = to_number(args[0])
        else:
            ms = float(int(_time.time() * 1000))
        d.set("__ms__", ms)

        def get_time(vm2, this2, a2):
            return d.get("__ms__")

        d.set("getTime", _native("Date.getTime", get_time))
        return d

    ctor = _native("Date", construct)
    return ctor


def install(env):
    """Install builtins as globals into an Environment."""
    env.define("console", make_console())
    env.define("Math", make_math())
    env.define("Date", make_date_constructor())

    def _parse_int(vm, this, args):
        s = to_js_string(args[0]) if args else ""
        try:
            return float(int(s.strip(), 10))
        except ValueError:
            return float("nan")

    def _parse_float(vm, this, args):
        return to_number(args[0]) if args else float("nan")

    def _is_nan(vm, this, args):
        n = to_number(args[0]) if args else float("nan")
        return n != n

    env.define("parseInt", _native("parseInt", _parse_int))
    env.define("parseFloat", _native("parseFloat", _parse_float))
    env.define("isNaN", _native("isNaN", _is_nan))
    return env
