"""Opcode set for the PyJS bytecode VM (frozen V1 instruction set).

All operands are integers (slots, jump targets, constant-pool indices, argc,
element counts). Names/functions/non-int literals live in the constant pool.

Store opcodes LEAVE their value on the stack (assignment-as-expression);
declarations emit a trailing POP. There is no DEFINE_GLOBAL; declaration
bookkeeping is handled by the compiler + STORE_GLOBAL/define-global semantics.
"""
from enum import IntEnum, auto


class OpCode(IntEnum):
    # constants / literals
    LOAD_CONST = auto()
    LOAD_TRUE = auto()
    LOAD_FALSE = auto()
    LOAD_NULL = auto()
    LOAD_UNDEFINED = auto()
    # variables
    LOAD_LOCAL = auto()
    STORE_LOCAL = auto()
    DEFINE_GLOBAL = auto()   # initial binding; operand = const idx of name
    LOAD_GLOBAL = auto()
    STORE_GLOBAL = auto()
    LOAD_UPVALUE = auto()
    STORE_UPVALUE = auto()
    CLOSE_UPVALUE = auto()   # close upvalue for top-of-stack local, then pop
    # arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    POW = auto()
    NEG = auto()
    # comparison
    EQ = auto()
    NEQ = auto()
    STRICT_EQ = auto()
    STRICT_NEQ = auto()
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()
    # logical / unary
    NOT = auto()
    TYPEOF = auto()
    # `this` binding
    LOAD_THIS = auto()       # push the current frame's `this`
    # control flow
    JUMP = auto()
    JUMP_IF_FALSE = auto()      # pops condition
    JUMP_IF_TRUE = auto()       # pops condition
    JUMP_IF_FALSE_KEEP = auto()  # peeks; used for && short-circuit
    JUMP_IF_TRUE_KEEP = auto()   # peeks; used for || short-circuit
    POP = auto()
    DUP = auto()
    # functions
    MAKE_CLOSURE = auto()    # operand = const idx of JSFunction
    CALL = auto()            # operand = argc
    CALL_METHOD = auto()     # operand = argc; receiver passed as this
    RETURN = auto()
    # arrays / objects
    BUILD_ARRAY = auto()         # operand = element count
    BUILD_ARRAY_SPREAD = auto()  # operand = element count (tagged elements)
    BUILD_OBJECT = auto()        # operand = pair count
    GET_INDEX = auto()
    SET_INDEX = auto()
    GET_PROP = auto()        # operand = const idx of name
    SET_PROP = auto()        # operand = const idx of name
    # spread support for calls
    SPREAD = auto()          # mark top-of-stack array as spread element
    CALL_SPREAD = auto()     # operand = segment count; args pre-built as array
    HALT = auto()
