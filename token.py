T_LET = "LET"
T_IDENTIFIER = "IDENTIFIER"
T_NUMBER = "NUMBER"
T_ASSIGN = "ASSIGN"
T_SEMICOLON = "SEMICOLON"
T_EOF = "EOF"


class Token:
  def __init__(self,type,value):
    self.type = type
    self.value = value
  
  def __repr__(self):
    return f"Type = {self.type} ; Value = {self.value}"
  

class Lexer:
  def __init__(self,source_code,pos = -1):
    self.source_code = source_code
    self.pos = pos
    self.curr_char = ""

  def advance(self):
    self.pos += 1
    self.curr_char = self.source_code[self.pos] if self.pos < len(self.source_code) else None
  
  def read_lexer(self):
    word =""
    while self.curr_char != " " and self.curr_char != None :
      word += self.curr_char
      self.advance()
    return word
  
  def create_lexer_token(self):
    word_created = self.read_lexer()

    if word_created == "let":
      return Token(T_LET, word_created)
    
    if type(int(word_created)) == int:
      return TOKEN(T_NUMBER , word_created)

    return Token(T_IDENTIFIER, word_created)
  
lexer = Lexer("num")

token = lexer.create_lexer_token()
print(token)