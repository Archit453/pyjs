#######################################
# TOKENS
#######################################


# =========================
# LITERALS
# =========================

T_NUMBER = "NUMBER"
T_STRING = "STRING"

T_TRUE = "TRUE"
T_FALSE = "FALSE"
T_NULL = "NULL"
T_UNDEFINED = "UNDEFINED"

# =========================
# IDENTIFIERS & VARIABLES
# =========================

T_IDENTIFIER = "IDENTIFIER"

T_LET = "LET"
T_CONST = "CONST"

# =========================
# ASSIGNMENT
# =========================

T_ASSIGN = "ASSIGN"

# =========================
# ARITHMETIC OPERATORS
# =========================

T_PLUS = "PLUS"
T_MINUS = "MINUS"
T_MUL = "MUL"
T_DIV = "DIV"
T_MOD = "MOD"

# =========================
# COMPARISON OPERATORS
# =========================

T_EQ = "EQ"                   # ==
T_STRICT_EQ = "STRICT_EQ"     # ===

T_NEQ = "NEQ"                 # !=
T_STRICT_NEQ = "STRICT_NEQ"   # !==

T_LT = "LT"
T_GT = "GT"
T_LTE = "LTE"
T_GTE = "GTE"

# =========================
# LOGICAL OPERATORS
# =========================

T_AND = "AND"                 # &&
T_OR = "OR"                   # ||
T_NOT = "NOT"                 # !

# =========================
# DELIMITERS
# =========================

T_COMMA = "COMMA"
T_DOT = "DOT"
T_COLON = "COLON"
T_SEMICOLON = "SEMICOLON"

# =========================
# BRACKETS
# =========================

T_LPAREN = "LPAREN"
T_RPAREN = "RPAREN"

T_LBRACE = "LBRACE"
T_RBRACE = "RBRACE"

T_LBRACKET = "LBRACKET"
T_RBRACKET = "RBRACKET"

# =========================
# CONTROL FLOW
# =========================

T_IF = "IF"
T_ELSE = "ELSE"

T_WHILE = "WHILE"
T_FOR = "FOR"

# =========================
# FUNCTIONS
# =========================

T_FUNCTION = "FUNCTION"
T_RETURN = "RETURN"
T_ARROW = "ARROW"       # =>
T_SPREAD = "SPREAD"     # ...

T_DO = "DO"

T_SWITCH = "SWITCH"
T_CASE = "CASE"
T_DEFAULT = "DEFAULT"
T_BREAK = "BREAK"

# =========================
# SPECIAL
# =========================

T_EOF = "EOF"

# =========================
# KEYWORDS
# =========================

KEYWORDS = {
    "let": T_LET,
    "const": T_CONST,

    "if": T_IF,
    "else": T_ELSE,

    "while": T_WHILE,
    "for": T_FOR,

    "function": T_FUNCTION,
    "return": T_RETURN,

    "true": T_TRUE,
    "false": T_FALSE,

    "null": T_NULL,
    "undefined": T_UNDEFINED,

    "do": T_DO,

    "switch": T_SWITCH,
    "case": T_CASE,
    "default": T_DEFAULT,
    "break": T_BREAK,
}

class Token:
    def __init__(
        self,
        type,
        value,
        pos_start=None,
        pos_end=None
    ):
        self.type = type
        self.value = value

        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return (
            f"Token({self.type}, {self.value}, "
            f"{self.pos_start}->{self.pos_end})"
        )

#######################################
# POSITION
#######################################

class Position:
    def __init__(self, index, line, column):
        self.index = index
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f"{self.line}:{self.column}"

    def copy(self):
        return Position(
            self.index,
            self.line,
            self.column
        )


#######################################
# LEXER
#######################################


class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.position = Position(0, 1, 1)
        self.curr_char = source_code[0] if source_code else None

    def advance(self):
        if self.curr_char == "\n":
            self.position.line += 1
            self.position.column = 1
        else:
            self.position.column += 1

        self.position.index += 1

        if self.position.index < len(self.source_code):
            self.curr_char = self.source_code[self.position.index]
        else:
            self.curr_char = None

    def make_token(self, token_type, value, pos_start):
        return Token(
            token_type,
            value,
            pos_start,
            self.position.copy()
        )
    
    def skip_whitespace(self):
        while self.curr_char is not None and self.curr_char.isspace():
            self.advance()

    def skip_single_line_comment(self):
        while (
            self.curr_char is not None
            and self.curr_char != "\n"
        ):
            self.advance()

    def skip_multi_line_comment(self):
        self.advance()  # skip *
        
        while self.curr_char is not None:

            if self.curr_char == "*":
                self.advance()

                if self.curr_char == "/":
                    self.advance()
                    return

            else:
                self.advance()

        raise Exception("Unterminated comment")

    def read_identifier(self):
        word = ""

        while (
            self.curr_char is not None
            and (
                self.curr_char.isalnum()
                or self.curr_char == "_"
                or self.curr_char == "$"
            )
        ):
            word += self.curr_char
            self.advance()

        return word

    def read_number(self):
        number = ""
        dot_count = 0

        while self.curr_char is not None:

            if self.curr_char.isdigit():
                number += self.curr_char
                self.advance()

            elif self.curr_char == ".":

                if dot_count == 1:
                    break

                dot_count += 1
                number += "."
                self.advance()

            else:
                break

        if number.startswith("."):
            number = "0" + number

        if number.endswith("."):
            number += "0"

        if dot_count == 0:
            return int(number)

        return float(number)
    def read_string(self):
        quote_char = self.curr_char

        self.advance()

        string = ""

        while (
            self.curr_char is not None
            and self.curr_char != quote_char
        ):
            string += self.curr_char
            self.advance()

        if self.curr_char != quote_char:
            raise Exception("Unterminated string")

        self.advance()

        return string

    def get_next_token(self):
        while self.curr_char is not None:

            if self.curr_char.isspace():
                self.skip_whitespace()
                continue

            if self.curr_char.isalpha() or self.curr_char == "_" or self.curr_char == "$":
                start = self.position.copy()

                word = self.read_identifier()

                token_type = KEYWORDS.get(word, T_IDENTIFIER)

                return self.make_token(
                    token_type,
                    word,
                    start
                )

            if (
                self.curr_char.isdigit()
                or (
                    self.curr_char == "."
                    and self.position.index + 1 < len(self.source_code)
                    and self.source_code[self.position.index + 1].isdigit()
                )
            ):
                start = self.position.copy()

                value = self.read_number()

                return self.make_token(
                    T_NUMBER,
                    value,
                    start
                )

            if self.curr_char in ['"', "'"]:
                start = self.position.copy()

                value = self.read_string()

                return self.make_token(
                    T_STRING,
                    value,
                    start
                )

            if self.curr_char == ";":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_SEMICOLON, ";", start)

            if self.curr_char == "+":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_PLUS, "+", start)

            if self.curr_char == "-":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_MINUS, "-", start)

            if self.curr_char == "*":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_MUL, "*", start)

            if self.curr_char == "/":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "/":
                    self.skip_single_line_comment()
                    continue

                if self.curr_char == "*":
                    self.skip_multi_line_comment()
                    continue

                return self.make_token(T_DIV, "/", start)

            if self.curr_char == "%":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_MOD, "%", start)

            if self.curr_char == "<":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "=":
                    self.advance()
                    return self.make_token(T_LTE, "<=", start)

                return self.make_token(T_LT, "<", start)

            if self.curr_char == ">":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "=":
                    self.advance()
                    return self.make_token(T_GTE, ">=", start)

                return self.make_token(T_GT, ">", start)

            if self.curr_char == "(":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_LPAREN, "(", start)

            if self.curr_char == ")":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_RPAREN, ")", start)

            if self.curr_char == "{":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_LBRACE, "{", start)

            if self.curr_char == "}":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_RBRACE, "}", start)

            if self.curr_char == "[":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_LBRACKET, "[", start)

            if self.curr_char == "]":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_RBRACKET, "]", start)

            if self.curr_char == ",":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_COMMA, ",", start)

            if self.curr_char == ".":
                start = self.position.copy()

                self.advance()

                if self.curr_char == ".":
                    self.advance()

                    if self.curr_char == ".":
                        self.advance()
                        return self.make_token(T_SPREAD, "...", start)

                    raise Exception("Expected '.'")

                return self.make_token(T_DOT, ".", start)

            if self.curr_char == ":":
                start = self.position.copy()
                self.advance()
                return self.make_token(T_COLON, ":", start)

            if self.curr_char == "=":
                start = self.position.copy()

                self.advance()

                if self.curr_char == ">":
                    self.advance()
                    return self.make_token(T_ARROW, "=>", start)

                if self.curr_char == "=":
                    self.advance()

                    if self.curr_char == "=":
                        self.advance()
                        return self.make_token(T_STRICT_EQ, "===", start)

                    return self.make_token(T_EQ, "==", start)

                return self.make_token(T_ASSIGN, "=", start)

            if self.curr_char == "!":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "=":
                    self.advance()

                    if self.curr_char == "=":
                        self.advance()
                        return self.make_token(T_STRICT_NEQ, "!==", start)

                    return self.make_token(T_NEQ, "!=", start)

                return self.make_token(T_NOT, "!", start)

            if self.curr_char == "&":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "&":
                    self.advance()
                    return self.make_token(T_AND, "&&", start)

                raise Exception("Expected '&'")

            if self.curr_char == "|":
                start = self.position.copy()

                self.advance()

                if self.curr_char == "|":
                    self.advance()
                    return self.make_token(T_OR, "||", start)

                raise Exception("Expected '|'")

            raise Exception(
                f"Unexpected character: {self.curr_char}"
            )

        start = self.position.copy()

        return self.make_token(
            T_EOF,
            None,
            start
        )
    def tokenize(self):
      tokens = []

      while True:
          token = self.get_next_token()
          tokens.append(token)

          if token.type == T_EOF:
              break

      return tokens
    
lexer = Lexer("let arr = [...nums]")

for token in lexer.tokenize():
    print(token)
