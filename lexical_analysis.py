T_LET = "LET"
T_IDENTIFIER = "IDENTIFIER"
T_NUMBER = "NUMBER"
T_ASSIGN = "ASSIGN"
T_PLUS = "PLUS"
T_MINUS = "MINUS"
T_SEMICOLON = "SEMICOLON"
T_EOF = "EOF"



class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value})"


class Lexer:
    def __init__(self, source_code):
        self.source_code = source_code
        self.pos = 0
        self.curr_char = source_code[0] if source_code else None

    def advance(self):
        self.pos += 1

        if self.pos < len(self.source_code):
            self.curr_char = self.source_code[self.pos]
        else:
            self.curr_char = None

    def skip_whitespace(self):
        while self.curr_char is not None and self.curr_char.isspace():
            self.advance()

    def read_identifier(self):
        word = ""

        while (
            self.curr_char is not None
            and (self.curr_char.isalnum() or self.curr_char == "_")
        ):
            word += self.curr_char
            self.advance()

        return word

    def read_number(self):
        number = ""

        while self.curr_char is not None and self.curr_char.isdigit():
            number += self.curr_char
            self.advance()

        return number

    def get_next_token(self):

        while self.curr_char is not None:

            if self.curr_char.isspace():
                self.skip_whitespace()
                continue

            if self.curr_char.isalpha() or self.curr_char == "_":

                word = self.read_identifier()

                if word == "let":
                    return Token(T_LET, word)

                return Token(T_IDENTIFIER, word)

            if self.curr_char.isdigit():
                return Token(T_NUMBER, self.read_number())

            if self.curr_char == "=":
                self.advance()
                return Token(T_ASSIGN, "=")

            if self.curr_char == ";":
                self.advance()
                return Token(T_SEMICOLON, ";")

            raise Exception(f"Unexpected character: {self.curr_char}")

        return Token(T_EOF, None)
    def tokenize(self):
      tokens = []

      while True:
          token = self.get_next_token()
          tokens.append(token)

          if token.type == T_EOF:
              break

      return tokens
    
