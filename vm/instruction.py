"""Instruction objects and the CodeObject bytecode container.

An Instruction couples an OpCode with an integer operand (or None). A
CodeObject is the immutable compiled body of a function (or the top-level
script): bytecode + constant pool + metadata used by the VM and MAKE_CLOSURE.

Constant dedup applies only to immutable primitives (str/float/bool). Objects
and functions are never deduplicated (each definition is unique).
"""
from .opcode import OpCode


class Instruction:
    __slots__ = ("op", "operand", "line")

    def __init__(self, op, operand=None, line=0):
        self.op = op
        self.operand = operand
        self.line = line

    def __repr__(self):
        if self.operand is None:
            return self.op.name
        return f"{self.op.name} {self.operand}"


class CodeObject:
    """Immutable compiled body of a function or the top-level script."""

    def __init__(self, name="<script>", arity=0, has_rest=False):
        self.name = name
        self.arity = arity
        self.has_rest = has_rest
        self.code = []          # list[Instruction]
        self.constants = []     # constant pool (any runtime value)
        self.num_locals = 0     # stack slots to reserve for locals on entry
        self.upvalues = []      # list[(is_local: bool, index: int)]
        # Phase 4 fix: const-global names were previously stashed on __dict__
        # by the compiler. Make it a real attribute so it is always present
        # and reliably readable by the VM.
        self.const_globals = set()

    # -- constant pool --
    def add_const(self, value):
        if isinstance(value, (str, bool, float)):
            for i, c in enumerate(self.constants):
                # bool before float: True is not 1.0 here.
                if type(c) is type(value) and c == value:
                    return i
        self.constants.append(value)
        return len(self.constants) - 1

    # -- emission --
    def emit(self, op, operand=None, line=0):
        self.code.append(Instruction(op, operand, line))
        return len(self.code) - 1

    def add_upvalue(self, is_local, index):
        for i, (l, idx) in enumerate(self.upvalues):
            if l == is_local and idx == index:
                return i
        self.upvalues.append((is_local, index))
        return len(self.upvalues) - 1

    # -- jump patching --
    def patch_jump(self, instr_index, target=None):
        if target is None:
            target = len(self.code)
        self.code[instr_index].operand = target

    def here(self):
        return len(self.code)

    # -- debugging --
    def disassemble(self):
        lines = [f"== {self.name} (arity={self.arity}, locals={self.num_locals}) =="]
        for i, ins in enumerate(self.code):
            lines.append(f"{i:04d}  {ins}")
        for j, fn in enumerate(self.constants):
            inner = getattr(fn, "code", None)
            if inner is not None and hasattr(inner, "disassemble"):
                lines.append("")
                lines.append(inner.disassemble())
        return "\n".join(lines)
