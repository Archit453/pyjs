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
    
class BlockStatementNode:
    def __init__(self, body):
        self.body = body

    def __repr__(self):
        return f"BlockStatementNode({self.body})"
    
class FunctionDeclarationNode:
    def __init__(self, name, parameters, body):
        self.name = name
        self.parameters = parameters
        self.body = body

    def __repr__(self):
        return (
            f"FunctionDeclarationNode("
            f"{self.name}, "
            f"{self.parameters}, "
            f"{self.body})"
        )
class FunctionExpressionNode:
    def __init__(self, parameters, body):
        self.parameters = parameters
        self.body = body

    def __repr__(self):
        return (
            f"FunctionExpressionNode("
            f"{self.parameters}, "
            f"{self.body})"
        )
    
class ArrowFunctionNode:
    def __init__(self, parameters, body):
        self.parameters = parameters
        self.body = body

    def __repr__(self):
        return (
            f"ArrowFunctionNode("
            f"{self.parameters}, "
            f"{self.body})"
        )
    
class IfStatementNode:
    def __init__(self, condition, consequent, alternate=None):
        self.condition = condition
        self.consequent = consequent
        self.alternate = alternate

    def __repr__(self):
        return (
            f"IfStatementNode("
            f"{self.condition}, "
            f"{self.consequent}, "
            f"{self.alternate})"
        )
    
class SwitchStatementNode:
    def __init__(self, discriminant, cases):
        self.discriminant = discriminant
        self.cases = cases

    def __repr__(self):
        return (
            f"SwitchStatementNode("
            f"{self.discriminant}, "
            f"{self.cases})"
        )
class SwitchCaseNode:
    def __init__(self, test, consequent):
        self.test = test
        self.consequent = consequent

    def __repr__(self):
        return (
            f"SwitchCaseNode("
            f"{self.test}, "
            f"{self.consequent})"
        )
    
class BreakStatementNode:
    def __repr__(self):
        return "BreakStatementNode()"
    
class ContinueStatementNode:
    def __repr__(self):
        return "ContinueStatementNode()"
    
class WhileStatementNode:
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return (
            f"WhileStatementNode("
            f"{self.condition}, "
            f"{self.body})"
        )
    
class DoWhileStatementNode:
    def __init__(self, body, condition):
        self.body = body
        self.condition = condition

    def __repr__(self):
        return (
            f"DoWhileStatementNode("
            f"{self.body}, "
            f"{self.condition})"
        )
    
class AssignmentExpressionNode:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return (
            f"AssignmentExpressionNode("
            f"{self.left}, "
            f"{self.right})"
        )
    
class ForStatementNode:
    def __init__(
        self,
        initializer,
        condition,
        update,
        body
    ):
        self.initializer = initializer
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return (
            f"ForStatementNode("
            f"{self.initializer}, "
            f"{self.condition}, "
            f"{self.update}, "
            f"{self.body})"
        )
    
class ComputedMemberExpressionNode:
    def __init__(self, object, property):
        self.object = object
        self.property = property

    def __repr__(self):
        return (
            f"ComputedMemberExpressionNode("
            f"{self.object}, "
            f"{self.property})"
        )
    
    