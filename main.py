from lexical_analysis import Lexer
from parser import Parser

from runtime.interpreter import Interpreter

lexer = Lexer("""
function add(a,b){
    return a+b;
}

let user = {
    name: "Archit"
};

let arr = [10,20,30];

console.log(
    add(arr[0], arr[1])
);

console.log(
    user.name
);
""")

parser = Parser(lexer)

ast = parser.parse()

print(ast)

interpreter = Interpreter()

interpreter.evaluate(ast)

print(
    interpreter.environment.variables
)