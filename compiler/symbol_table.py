
"""Symbol table / scope resolution for the PyJS compiler.

Responsibilities (frozen architecture):
  * allocate local stack slots (with a high-water mark for num_locals)
  * track lexical block depth and pop symbols on scope exit
  * carry `kind` (let/const/function/param) for compile-time const enforcement
  * classify names as LOCAL / UPVALUE / GLOBAL
  * compute upvalue capture chains through enclosing functions

One SymbolTable instance exists per function compiler. Nested functions link
via `enclosing` so resolve_upvalue can walk outward.
"""

LOCAL = "local"
UPVALUE = "upvalue"
GLOBAL = "global"

LET = "let"
CONST = "const"
FUNCTION = "function"
PARAM = "param"


class Symbol:
    __slots__ = ("name", "slot", "depth", "kind", "is_captured")

    def __init__(self, name, slot, depth, kind):
        self.name = name
        self.slot = slot
        self.depth = depth
        self.kind = kind
        self.is_captured = False


class SymbolTable:
    def __init__(self, enclosing=None, is_function_root=True):
        self.enclosing = enclosing            # enclosing SymbolTable or None
        self.scopes_locals = []               # active Symbol list (stack order)
        self.scope_depth = 0
        self.next_slot = 0
        self.max_slots = 0
        self.upvalues = []                    # list[(is_local, index)]
        self.is_function_root = is_function_root

    # -- scope management --
    def begin_scope(self):
        self.scope_depth += 1

    def end_scope(self):
        """Pop symbols declared at the current depth.

        Returns the list of popped Symbols (so the compiler can emit
        CLOSE_UPVALUE for captured ones) in reverse declaration order.
        """
        popped = []
        while self.scopes_locals and self.scopes_locals[-1].depth == self.scope_depth:
            sym = self.scopes_locals.pop()
            self.next_slot -= 1
            popped.append(sym)
        self.scope_depth -= 1
        return popped

    # -- declaration --
    def declare(self, name, kind):
        """Declare a local in the current scope. Returns the Symbol.

        Raises ValueError on redeclaration within the same depth.
        """
        for sym in reversed(self.scopes_locals):
            if sym.depth != self.scope_depth:
                break
            if sym.name == name:
                raise ValueError(
                    f"Identifier '{name}' has already been declared")
        slot = self.next_slot
        self.next_slot += 1
        if self.next_slot > self.max_slots:
            self.max_slots = self.next_slot
        sym = Symbol(name, slot, self.scope_depth, kind)
        self.scopes_locals.append(sym)
        return sym

    def reserve_slot(self):
        """Reserve an anonymous local slot (e.g. switch discriminant temp)."""
        slot = self.next_slot
        self.next_slot += 1
        if self.next_slot > self.max_slots:
            self.max_slots = self.next_slot
        return slot

    def release_slot(self):
        self.next_slot -= 1

    # -- resolution --
    def resolve_local(self, name):
        for sym in reversed(self.scopes_locals):
            if sym.name == name:
                return sym
        return None

    def resolve_upvalue(self, name):
        """Resolve `name` as an upvalue. Returns upvalue index or None."""
        if self.enclosing is None:
            return None
        local = self.enclosing.resolve_local(name)
        if local is not None:
            local.is_captured = True
            return self._add_upvalue(True, local.slot)
        outer = self.enclosing.resolve_upvalue(name)
        if outer is not None:
            return self._add_upvalue(False, outer)
        return None

    def _add_upvalue(self, is_local, index):
        for i, (l, idx) in enumerate(self.upvalues):
            if l == is_local and idx == index:
                return i
        self.upvalues.append((is_local, index))
        return len(self.upvalues) - 1

    def resolve(self, name):
        """Classify a name. Returns (kind_str, payload).

        ('local', Symbol) | ('upvalue', index) | ('global', name)
        """
        sym = self.resolve_local(name)
        if sym is not None:
            return (LOCAL, sym)
        up = self.resolve_upvalue(name)
        if up is not None:
            return (UPVALUE, up)
        return (GLOBAL, name)
