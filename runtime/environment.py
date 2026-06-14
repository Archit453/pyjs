"""Global environment for PyJS.

The global object is a name-keyed dictionary. `const` globals are tracked in a
frozen set so STORE_GLOBAL can raise on reassignment (runtime half of const
enforcement; the compile-time half lives in the symbol table).

Name-based global resolution is retained per the frozen architecture; a
global-index cache is a reserved future optimization.
"""

from .values import UNDEFINED


class PyJSRuntimeError(Exception):
    """Structured runtime error carrying an optional source line."""

    def __init__(self, message, line=0):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self):
        if self.line:
            return f"{self.message} (line {self.line})"
        return self.message


class Environment:
    def __init__(self):
        self.globals = {}
        self.frozen = set()

    def define(self, name, value, is_const=False):
        self.globals[name] = value
        if is_const:
            self.frozen.add(name)

    def has(self, name):
        return name in self.globals

    def get(self, name):
        if name not in self.globals:
            raise PyJSRuntimeError(f"{name} is not defined")
        return self.globals[name]

    def assign(self, name, value):
        if name in self.frozen:
            raise PyJSRuntimeError(
                f"Assignment to constant variable '{name}'")
        # Plain assignment to an undeclared global creates it (sloppy mode).
        self.globals[name] = value
        return value

    def get_or_undefined(self, name):
        return self.globals.get(name, UNDEFINED)
