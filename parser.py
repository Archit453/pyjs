from lexical_analysis import *
from ast_nodes import *

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def advance(self):
        self.current_token = self.lexer.get_next_token()
        
    def expression(self):

        if self.current_token.type == T_NUMBER:
            node = NumberNode(self.current_token)
            self.eat(T_NUMBER)
            return node

        if self.current_token.type == T_IDENTIFIER:
            node = IdentifierNode(self.current_token)
            self.eat(T_IDENTIFIER)
            return node

        raise Exception(
            f"Expected NUMBER or IDENTIFIER, got {self.current_token.type}"
        )      

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.advance()
        else:
            raise Exception(
                f"Expected {token_type}, got {self.current_token.type}"
            )

    def parse_variable_declaration(self):

        self.eat(T_LET)

        identifier = IdentifierNode(self.current_token)
        self.eat(T_IDENTIFIER)

        self.eat(T_ASSIGN)

        value = self.expression()

        self.eat(T_SEMICOLON)

        return VariableDeclarationNode(identifier, value)

    def parse(self):
        return self.parse_variable_declaration()
    
