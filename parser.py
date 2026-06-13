from lexical_analysis import *
from ast_nodes import *


class Parser:
    def __init__(self, lexer):
        self.tokens = lexer.tokenize()
        self.index = 0
        self.current_token = self.tokens[self.index]

    def advance(self):
        self.index += 1

        if self.index < len(self.tokens):
            self.current_token = self.tokens[self.index]
    
    def peek(self, offset=1):
        position = self.index + offset

        if position < len(self.tokens):
            return self.tokens[position]

        return None
            
    def match(self, token_type):
        return (
            self.current_token is not None
            and self.current_token.type == token_type
        )
    
    def check(self, offset, token_type):
        token = self.peek(offset)

        return (
            token is not None
            and token.type == token_type
        )
    
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
        
        if self.current_token.type == T_FUNCTION:
            return self.function_expression()
        
        if (
            self.match(T_IDENTIFIER)
            and self.check(1, T_ARROW)
        ):
            return self.arrow_function_single()
        
        if self.current_token.type == T_IDENTIFIER:
            node = IdentifierNode(self.current_token)
            self.eat(T_IDENTIFIER)
            return node
        if self.is_arrow_function():
            return self.arrow_function_multiple()
        
        if self.current_token.type == T_LPAREN:
            self.eat(T_LPAREN)
            node = self.expression()
            self.eat(T_RPAREN)
            return node

        raise Exception(
            f"Expected NUMBER or IDENTIFIER, got {self.current_token.type}"
        )
    def statement(self):
        if self.current_token.type == T_IF:
            return self.parse_if_statement()
        if self.current_token.type == T_SWITCH:
            return self.parse_switch_statement()
        if self.current_token.type == T_BREAK:
            return self.parse_break_statement()
        if self.current_token.type == T_CONTINUE:
            return self.parse_continue_statement()
        if self.current_token.type == T_WHILE:
            return self.parse_while_statement()
        if self.current_token.type == T_DO:
            return self.parse_do_while_statement()
        if self.current_token.type == T_FOR:
            return self.parse_for_statement()
        if self.current_token.type == T_FUNCTION:
            return self.parse_function_declaration()
        if self.match(T_LET):
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
    def is_arrow_function(self):

        if not self.match(T_LPAREN):
            return False

        offset = 1
        expect_identifier = True

        while True:

            token = self.peek(offset)

            if token is None:
                return False

            if expect_identifier:

                if token.type == T_RPAREN:

                    next_token = self.peek(offset + 1)

                    return (
                        next_token is not None
                        and next_token.type == T_ARROW
                    )

                if token.type != T_IDENTIFIER:
                    return False

                expect_identifier = False

            else:

                if token.type == T_COMMA:
                    expect_identifier = True

                elif token.type == T_RPAREN:

                    next_token = self.peek(offset + 1)

                    return (
                        next_token is not None
                        and next_token.type == T_ARROW
                    )

                else:
                    return False

            offset += 1
    def block_statement(self):
        body = []

        self.eat(T_LBRACE)

        while self.current_token.type != T_RBRACE:

            body.append(
                self.statement()
            )

        self.eat(T_RBRACE)

        return BlockStatementNode(body)

    def function_parameters(self):
        parameters = []

        self.eat(T_LPAREN)

        if self.current_token.type != T_RPAREN:

            parameters.append(
                IdentifierNode(
                    self.current_token
                )
            )

            self.eat(T_IDENTIFIER)

            while self.current_token.type == T_COMMA:

                self.eat(T_COMMA)

                parameters.append(
                    IdentifierNode(
                        self.current_token
                    )
                )

                self.eat(T_IDENTIFIER)

        self.eat(T_RPAREN)

        return parameters
    def function_expression(self):

        self.eat(T_FUNCTION)

        parameters = self.function_parameters()

        body = self.block_statement()

        return FunctionExpressionNode(
            parameters,
            body
        )
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

        while self.current_token.type in (
            T_DOT,
            T_LBRACKET
        ):

            if self.current_token.type == T_DOT:

                self.eat(T_DOT)

                property = IdentifierNode(
                    self.current_token
                )

                self.eat(T_IDENTIFIER)

                object = MemberExpressionNode(
                    object,
                    property
                )

            elif self.current_token.type == T_LBRACKET:

                self.eat(T_LBRACKET)

                property = self.expression()

                self.eat(T_RBRACKET)

                object = ComputedMemberExpressionNode(
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
    def assignment(self):

        left = self.logical_or()

        if self.current_token.type == T_ASSIGN:

            if not isinstance(
                left,
                (
                    IdentifierNode,
                    MemberExpressionNode,
                    ComputedMemberExpressionNode
                )
            ):
                raise Exception(
                    "Invalid assignment target"
                )

            self.eat(T_ASSIGN)

            right = self.assignment()

            return AssignmentExpressionNode(
                left,
                right
            )

        return left
    def expression(self):
        return self.assignment()

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

        value = None

        if self.current_token.type != T_SEMICOLON:
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
    def parse_function_declaration(self):
        self.eat(T_FUNCTION)

        name = IdentifierNode(
            self.current_token
        )

        self.eat(T_IDENTIFIER)

        parameters = self.function_parameters()

        body = self.block_statement()

        return FunctionDeclarationNode(
            name,
            parameters,
            body
        )
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
    
    def arrow_function_single(self):

        parameter = IdentifierNode(
            self.current_token
        )

        self.eat(T_IDENTIFIER)

        self.eat(T_ARROW)

        if self.current_token.type == T_LBRACE:
            body = self.block_statement()
        else:
            body = self.expression()

        return ArrowFunctionNode(
            [parameter],
            body
        )

    def arrow_function_multiple(self):

        parameters = []

        self.eat(T_LPAREN)

        if self.current_token.type != T_RPAREN:

            parameters.append(
                IdentifierNode(self.current_token)
            )

            self.eat(T_IDENTIFIER)

            while self.current_token.type == T_COMMA:

                self.eat(T_COMMA)

                parameters.append(
                    IdentifierNode(self.current_token)
                )

                self.eat(T_IDENTIFIER)

        self.eat(T_RPAREN)

        self.eat(T_ARROW)

        if self.current_token.type == T_LBRACE:
            body = self.block_statement()
        else:
            body = self.expression()

        return ArrowFunctionNode(
            parameters,
            body
        )
    
    def parse_if_statement(self):
        self.eat(T_IF)

        self.eat(T_LPAREN)

        condition = self.expression()

        self.eat(T_RPAREN)

        consequent = self.block_statement()
        alternate = None

        if self.current_token.type == T_ELSE:
            self.eat(T_ELSE)

            if self.current_token.type == T_IF:
                alternate = self.parse_if_statement()
            else:
                alternate = self.block_statement()

        return IfStatementNode(
            condition,
            consequent,
            alternate
        )
    def parse_switch_statement(self):
        self.eat(T_SWITCH)

        self.eat(T_LPAREN)

        discriminant = self.expression()

        self.eat(T_RPAREN)

        self.eat(T_LBRACE)

        cases = []

        while self.current_token.type != T_RBRACE:

            cases.append(
                self.parse_switch_case()
            )

        self.eat(T_RBRACE)

        return SwitchStatementNode(
            discriminant,
            cases
        )
    def parse_switch_case(self):
        if self.current_token.type == T_CASE:

            self.eat(T_CASE)

            test = self.expression()

        else:

            self.eat(T_DEFAULT)

            test = None

        self.eat(T_COLON)

        consequent = []

        while self.current_token.type not in (
            T_CASE,
            T_DEFAULT,
            T_RBRACE
        ):

            consequent.append(
                self.statement()
            )

        return SwitchCaseNode(
            test,
            consequent
        )
    def parse_break_statement(self):
        self.eat(T_BREAK)

        self.eat(T_SEMICOLON)

        return BreakStatementNode()
    def parse_while_statement(self):
        self.eat(T_WHILE)

        self.eat(T_LPAREN)

        condition = self.expression()

        self.eat(T_RPAREN)

        body = self.block_statement()

        return WhileStatementNode(
            condition,
            body
        )
    def parse_do_while_statement(self):
        self.eat(T_DO)

        body = self.block_statement()

        self.eat(T_WHILE)

        self.eat(T_LPAREN)

        condition = self.expression()

        self.eat(T_RPAREN)

        self.eat(T_SEMICOLON)

        return DoWhileStatementNode(
            body,
            condition
        )
    def parse_for_statement(self):
        self.eat(T_FOR)

        self.eat(T_LPAREN)

        # ----------------
        # Initializer
        # ----------------
        initializer = None

        if self.current_token.type != T_SEMICOLON:

            if self.current_token.type in (
                T_LET,
                T_CONST
            ):
                initializer = self.parse_for_initializer()
            else:
                initializer = self.expression()

        self.eat(T_SEMICOLON)
        # ----------------
        # Condition
        # ----------------

        condition = None

        if self.current_token.type != T_SEMICOLON:
            condition = self.expression()

        self.eat(T_SEMICOLON)

        # ----------------
        # Update
        # ----------------

        update = None

        if self.current_token.type != T_RPAREN:
            update = self.expression()

        self.eat(T_RPAREN)

        body = self.block_statement()

        return ForStatementNode(
            initializer,
            condition,
            update,
            body
        )
    def parse_for_initializer(self):

        kind = self.current_token.type

        if kind == T_LET:
            self.eat(T_LET)
        else:
            self.eat(T_CONST)

        identifier = IdentifierNode(
            self.current_token
        )

        self.eat(T_IDENTIFIER)

        self.eat(T_ASSIGN)

        value = self.expression()

        return VariableDeclarationNode(
            identifier,
            value
        )
    def parse_continue_statement(self):

        self.eat(T_CONTINUE)

        self.eat(T_SEMICOLON)

        return ContinueStatementNode()
    
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
