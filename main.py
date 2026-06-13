from lexical_analysis import Lexer
from parser import Parser

lexer = Lexer(
 '''
add(1,2);
''')

parser = Parser(lexer)

ast = parser.parse()

print(ast)