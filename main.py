from lexical_analysis import Lexer
from parser import Parser

lexer = Lexer("let num = x;")

parser = Parser(lexer)

ast = parser.parse()

print(ast)