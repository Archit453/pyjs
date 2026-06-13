from lexical_analysis import Lexer
from parser import Parser

lexer = Lexer(
 '''
let x = 5;
let y = 10;
return x;
''')

parser = Parser(lexer)

ast = parser.parse()

print(ast)