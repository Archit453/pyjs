from lexical_analysis import Lexer
from parser import Parser

lexer = Lexer(
 '''
function test(a,b){

    if(a > b){
        return a;
    }

    while(a < 100){
        a = a + 1;

        if(a == 50){
            continue;
        }

        if(a == 75){
            break;
        }
    }

    return a;
}
''')

parser = Parser(lexer)

ast = parser.parse()

print(ast)