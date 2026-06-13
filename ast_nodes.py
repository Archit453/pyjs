class NumberNode:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"NumberNode({self.token.value})"


class IdentifierNode:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"IdentifierNode({self.token.value})"


class VariableDeclarationNode:
    def __init__(self, identifier, value):
        self.identifier = identifier
        self.value = value

    def __repr__(self):
        return f"VariableDeclarationNode({self.identifier}, {self.value})"
    
class BinaryExpressionNode:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.operator.value} {self.right})"
    
class ArrayNode:
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        return f"ArrayNode({self.elements})"
    
class PropertyNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return f"PropertyNode({self.key}: {self.value})"


class ObjectNode:
    def __init__(self, properties):
        self.properties = properties

    def __repr__(self):
        return f"ObjectNode({self.properties})"
    
    
class StringNode:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f'StringNode("{self.token.value}")'


class BooleanNode:
    def __init__(self, token):
        self.token = token

    def __repr__(self):
        return f"BooleanNode({self.token.value})"


class NullNode:
    def __repr__(self):
        return "NullNode()"


class UndefinedNode:
    def __repr__(self):
        return "UndefinedNode()"
    
class MemberExpressionNode:
    def __init__(self, object, property):
        self.object = object
        self.property = property

    def __repr__(self):
        return (
            f"MemberExpressionNode({self.object}.{self.property})"
        )

class CallExpressionNode:
    def __init__(self, callee, arguments):
        self.callee = callee
        self.arguments = arguments

    def __repr__(self):
        return (
            f"CallExpressionNode("
            f"{self.callee}, "
            f"{self.arguments})"
        )
    
class ExpressionStatementNode:
    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return f"ExpressionStatementNode({self.expression})"
    
class ReturnStatementNode:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"ReturnStatementNode({self.value})"
    
class ProgramNode:
    def __init__(self, body):
        self.body = body

    def __repr__(self):
        return f"ProgramNode({self.body})"