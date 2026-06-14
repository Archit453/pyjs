"""Hand-written lexer for PyJS (no regex).

Converts a source string into a flat list of Tokens terminated by EOF.

Design:
  * single dispatch loop branching on character class
  * longest-match operator scanning (3-char, then 2-char, then 1-char)
  * accurate 1-based line/column tracking; each token records the position of
    its first character
  * helpful errors with line/column via LexerError

This module depends only on lexer.token (Phase 2) and is independent of the
rest of the pipeline.
"""
from .token import Token, TokenType, KEYWORDS


class LexerError(Exception):
    """Raised on malformed input. Carries line/column for diagnostics."""

    def __init__(self, message, line, col):
        super().__init__(f"{message} at line {line}, col {col}")
        self.raw_message = message
        self.line = line
        self.col = col


_ID_START_EXTRA = "_$"

# Multi-character operator tables, consulted longest-first.
_THREE_CHAR = {
    "===": TokenType.STRICT_EQ,
    "!==": TokenType.STRICT_NEQ,
    "...": TokenType.SPREAD,
}
_TWO_CHAR = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    ">=": TokenType.GTE,
    "<=": TokenType.LTE,
    "&&": TokenType.AND,
    "||": TokenType.OR,
    "=>": TokenType.ARROW,
    "++": TokenType.INC,
    "--": TokenType.DEC,
    "+=": TokenType.PLUS_ASSIGN,
    "-=": TokenType.MINUS_ASSIGN,
    "**": TokenType.POW,
}
_ONE_CHAR = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    ":": TokenType.COLON,
    "?": TokenType.QUESTION,
    ".": TokenType.DOT,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "=": TokenType.ASSIGN,
    ">": TokenType.GT,
    "<": TokenType.LT,
    "!": TokenType.NOT,
}

_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
    "v": "\v",
    "0": "\0",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "`": "`",
    "\n": "",  # line continuation
}


class Lexer:
    def __init__(self, source):
        self.src = source
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []

    # -- cursor helpers --
    def _peek(self, offset=0):
        i = self.pos + offset
        if i < self.length:
            return self.src[i]
        return ""

    def _at_end(self):
        return self.pos >= self.length

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, type_, value, line, col):
        self.tokens.append(Token(type_, value, line, col))

    # -- main loop --
    def tokenize(self):
        while not self._at_end():
            ch = self._peek()
            if ch in " \t\r\n\f\v":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                self._skip_line_comment()
            elif ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
            elif ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
                self._scan_number()
            elif ch == '"' or ch == "'":
                self._scan_string(ch)
            elif ch.isalpha() or ch in _ID_START_EXTRA:
                self._scan_identifier()
            else:
                self._scan_operator()
        self._add(TokenType.EOF, None, self.line, self.col)
        return self.tokens

    # -- comments --
    def _skip_line_comment(self):
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self):
        start_line, start_col = self.line, self.col
        self._advance()  # /
        self._advance()  # *
        while not self._at_end():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        raise LexerError("Unterminated block comment", start_line, start_col)

    # -- numbers --
    def _scan_number(self):
        line, col = self.line, self.col
        start = self.pos
        seen_dot = False
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        if self._peek() == ".":
            seen_dot = True
            self._advance()
            if not self._peek().isdigit() and start == self.pos - 1:
                pass  # leading-dot form handled by caller condition
            while not self._at_end() and self._peek().isdigit():
                self._advance()
        if self._peek() in ("e", "E"):
            save = self.pos
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if not self._peek().isdigit():
                raise LexerError("Invalid number: missing exponent digits",
                                 self.line, self.col)
            while not self._at_end() and self._peek().isdigit():
                self._advance()
        lexeme = self.src[start:self.pos]
        try:
            value = float(lexeme)
        except ValueError:
            raise LexerError(f"Invalid number literal {lexeme!r}", line, col)
        _ = seen_dot
        self._add(TokenType.NUMBER, value, line, col)

    # -- strings --
    def _scan_string(self, quote):
        line, col = self.line, self.col
        self._advance()  # opening quote
        chars = []
        while not self._at_end() and self._peek() != quote:
            ch = self._peek()
            if ch == "\n":
                raise LexerError("Unterminated string literal", line, col)
            if ch == "\\":
                self._advance()  # backslash
                if self._at_end():
                    raise LexerError("Unterminated escape sequence",
                                     self.line, self.col)
                esc = self._advance()
                chars.append(_ESCAPES.get(esc, esc))
            else:
                chars.append(self._advance())
        if self._at_end():
            raise LexerError("Unterminated string literal", line, col)
        self._advance()  # closing quote
        self._add(TokenType.STRING, "".join(chars), line, col)

    # -- identifiers / keywords --
    def _scan_identifier(self):
        line, col = self.line, self.col
        start = self.pos
        while not self._at_end():
            ch = self._peek()
            if ch.isalnum() or ch in _ID_START_EXTRA:
                self._advance()
            else:
                break
        word = self.src[start:self.pos]
        type_ = KEYWORDS.get(word)
        if type_ is not None:
            self._add(type_, word, line, col)
        else:
            self._add(TokenType.IDENT, word, line, col)

    # -- operators / delimiters (longest match) --
    def _scan_operator(self):
        line, col = self.line, self.col
        three = self.src[self.pos:self.pos + 3]
        if three in _THREE_CHAR:
            self._advance(); self._advance(); self._advance()
            return self._add(_THREE_CHAR[three], three, line, col)
        two = self.src[self.pos:self.pos + 2]
        if two in _TWO_CHAR:
            self._advance(); self._advance()
            return self._add(_TWO_CHAR[two], two, line, col)
        one = self._peek()
        if one in _ONE_CHAR:
            self._advance()
            return self._add(_ONE_CHAR[one], one, line, col)
        raise LexerError(f"Unexpected character {one!r}", line, col)


def tokenize(source):
    """Convenience: tokenize a source string into a list of Tokens."""
    return Lexer(source).tokenize()
