from lexical_analysis import Lexer
from parser import Parser

lexer = Lexer(
 '''
(a,b)=>{
    return a+b;
};
''')

parser = Parser(lexer)

ast = parser.parse()

print(ast)