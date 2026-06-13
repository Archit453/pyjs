from lexical_analysis import *
from ast_nodes import *

class UnaryExpressionNode:
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return f"({self.operator.value}{self.operand})"
    
class SpreadElementNode:
    def __init__(self, argument):
        self.argument = argument

    def __repr__(self):
        return f"SpreadElementNode({self.argument})"

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()

    def advance(self):
        self.current_token = self.lexer.get_next_token()
        
    def primary(self):

        if self.current_token.type in (
            T_MINUS,
            T_NOT
        ):

            operator = self.current_token
            self.eat(operator.type)

            operand = self.primary()

            return UnaryExpressionNode(
                operator,
                operand
            )
        if self.current_token.type == T_LBRACKET:
            return self.array_expression()
        
        if self.current_token.type == T_LBRACE:
            return self.object_expression()
        
        if self.current_token.type == T_NUMBER:
            node = NumberNode(self.current_token)
            self.eat(T_NUMBER)
            return node
        if self.current_token.type == T_STRING:
            node = StringNode(self.current_token)
            self.eat(T_STRING)
            return node

        if self.current_token.type in (T_TRUE, T_FALSE):
            node = BooleanNode(self.current_token)
            self.eat(self.current_token.type)
            return node

        if self.current_token.type == T_NULL:
            self.eat(T_NULL)
            return NullNode()

        if self.current_token.type == T_UNDEFINED:
            self.eat(T_UNDEFINED)
            return UndefinedNode()
        
        if self.current_token.type == T_IDENTIFIER:
            node = IdentifierNode(self.current_token)
            self.eat(T_IDENTIFIER)
            return node
        
        if self.current_token.type == T_LPAREN:
            self.eat(T_LPAREN)
            node = self.expression()
            self.eat(T_RPAREN)
            return node

        raise Exception(
            f"Expected NUMBER or IDENTIFIER, got {self.current_token.type}"
        )
    def statement(self):

        if self.current_token.type == T_LET:
            return self.parse_variable_declaration()

        if self.current_token.type == T_RETURN:
            return self.parse_return_statement()

        expression = self.expression()

        self.eat(T_SEMICOLON)

        return ExpressionStatementNode(
            expression
        )
    def statements(self):

        statements = []

        while self.current_token.type != T_EOF:
            statements.append(
                self.statement()
            )

        return statements

    def arguments(self):
        arguments = []

        self.eat(T_LPAREN)

        if self.current_token.type != T_RPAREN:

            arguments.append(
                self.expression()
            )

            while self.current_token.type == T_COMMA:

                self.eat(T_COMMA)

                arguments.append(
                    self.expression()
                )

        self.eat(T_RPAREN)

        return arguments
    
    def call_expression(self):

        callee = self.member_expression()

        while self.current_token.type == T_LPAREN:

            arguments = self.arguments()

            callee = CallExpressionNode(
                callee,
                arguments
            )

        return callee
    
    def member_expression(self):
        object = self.primary()

        while self.current_token.type == T_DOT:

            self.eat(T_DOT)

            property = IdentifierNode(
                self.current_token
            )

            self.eat(T_IDENTIFIER)

            object = MemberExpressionNode(
                object,
                property
            )

        return object
    def binary_operation(self, parse_func, operators):

        left = parse_func()

        while self.current_token.type in operators:

            operator = self.current_token
            self.eat(operator.type)

            right = parse_func()

            left = BinaryExpressionNode(
                left,
                operator,
                right
            )

        return left

    def multiplication(self):

        return self.binary_operation(
            self.call_expression,
            (
                T_MUL,
                T_DIV,
                T_MOD
            )
        )
    def addition(self):

        return self.binary_operation(
            self.multiplication,
            (
                T_PLUS,
                T_MINUS
            )
        )
    def comparison(self):

        return self.binary_operation(
            self.addition,
            (
                T_LT,
                T_GT,
                T_LTE,
                T_GTE,
                T_EQ,
                T_NEQ,
                T_STRICT_EQ,
                T_STRICT_NEQ
            )
        )
    def logical_and(self):

        return self.binary_operation(
            self.comparison,
            (
                T_AND,
            )
        )

    def logical_or(self):

        return self.binary_operation(
            self.logical_and,
            (
                T_OR,
            )
        )

    def expression(self):
        return self.logical_or()

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
        return ProgramNode(
            self.statements()
        )

    def parse_return_statement(self):

        self.eat(T_RETURN)

        value = self.expression()

        self.eat(T_SEMICOLON)

        return ReturnStatementNode(value)

    def parse_array_element(self):
        if self.current_token.type == T_SPREAD:

            self.eat(T_SPREAD)

            return SpreadElementNode(
                self.expression()
            )

        return self.expression()
    
    def array_expression(self):
        elements = []

        self.eat(T_LBRACKET)

        if self.current_token.type != T_RBRACKET:

            elements.append(
                self.parse_array_element()
            )

            while self.current_token.type == T_COMMA:

                self.eat(T_COMMA)

                elements.append(
                    self.parse_array_element()
                )

        self.eat(T_RBRACKET)

        return ArrayNode(elements)
    
    def object_expression(self):
        properties = []

        self.eat(T_LBRACE)

        if self.current_token.type != T_RBRACE:

            key = IdentifierNode(self.current_token)
            self.eat(T_IDENTIFIER)

            self.eat(T_COLON)

            value = self.expression()

            properties.append(
                PropertyNode(key, value)
            )

            while self.current_token.type == T_COMMA:

                self.eat(T_COMMA)

                key = IdentifierNode(self.current_token)
                self.eat(T_IDENTIFIER)

                self.eat(T_COLON)

                value = self.expression()

                properties.append(
                    PropertyNode(key, value)
                )

        self.eat(T_RBRACE)

        return ObjectNode(properties)
