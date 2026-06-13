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