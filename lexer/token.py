"""Token definitions for PyJS.

Single source of truth for token kinds: the TokenType enum, the Token record,
and the keyword lookup table. No scanning logic lives here.

The token set matches the frozen architecture, including ternary (QUESTION /
COLON) and the spread/rest token (SPREAD).
"""
from enum import Enum, auto


class TokenType(Enum):
    # -- literals --
    NUMBER = auto()
    STRING = auto()
    IDENT = auto()

    # -- keywords --
    LET = auto()
    CONST = auto()
    IF = auto()
    ELSE = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    WHILE = auto()
    DO = auto()
    FOR = auto()
    BREAK = auto()
    CONTINUE = auto()
    FUNCTION = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    UNDEFINED = auto()
    NEW = auto()       # reserved for later phases
    TYPEOF = auto()    # reserved for later phases

    # -- delimiters --
    LPAREN = auto()    # (
    RPAREN = auto()    # )
    LBRACE = auto()    # {
    RBRACE = auto()    # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COMMA = auto()     # ,
    SEMICOLON = auto() # ;

    # -- punctuation / structural --
    DOT = auto()       # .
    SPREAD = auto()    # ...
    COLON = auto()     # :
    QUESTION = auto()  # ?
    ARROW = auto()     # =>

    # -- arithmetic operators --
    PLUS = auto()      # +
    MINUS = auto()     # -
    STAR = auto()      # *
    POW = auto()       # **
    SLASH = auto()     # /
    PERCENT = auto()   # %

    # -- assignment operators --
    ASSIGN = auto()        # =
    PLUS_ASSIGN = auto()   # +=
    MINUS_ASSIGN = auto()  # -=

    # -- comparison operators --
    EQ = auto()            # ==
    NEQ = auto()           # !=
    STRICT_EQ = auto()     # ===
    STRICT_NEQ = auto()    # !==
    GT = auto()            # >
    LT = auto()            # <
    GTE = auto()           # >=
    LTE = auto()           # <=

    # -- logical operators --
    AND = auto()       # &&
    OR = auto()        # ||
    NOT = auto()       # !

    # -- update operators --
    INC = auto()       # ++
    DEC = auto()       # --

    # -- end of input --
    EOF = auto()


KEYWORDS = {
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "switch": TokenType.SWITCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "while": TokenType.WHILE,
    "do": TokenType.DO,
    "for": TokenType.FOR,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "function": TokenType.FUNCTION,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "undefined": TokenType.UNDEFINED,
    "new": TokenType.NEW,
    "typeof": TokenType.TYPEOF,
}


class Token:
    """A single lexical token.

    Attributes:
        type:  a TokenType
        value: the token's runtime payload (float for NUMBER, str for STRING /
               IDENT, the raw lexeme for operators/keywords)
        line:  1-based line of the token's first character
        col:   1-based column of the token's first character
    """

    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line=0, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __eq__(self, other):
        return (
            isinstance(other, Token)
            and self.type == other.type
            and self.value == other.value
        )

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line}, col={self.col})"
