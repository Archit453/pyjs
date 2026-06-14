from ast_nodes import *

from runtime.values import *
from runtime.environment import *
from lexical_analysis import *

class BreakException(Exception):
    pass


class ContinueException(Exception):
    pass

class ReturnException(Exception):

    def __init__(self, value):
        self.value = value

class Interpreter:

    def __init__(self):
        self.environment = Environment()
        console = ObjectValue({
            "log": NativeFunctionValue(
                self.native_console_log
            )
        })

        self.environment.define(
            "console",
            console
        )
    def native_console_log(
      self,
      arguments
  ):

      values = []

      for argument in arguments:

          if hasattr(
              argument,
              "value"
          ):
              values.append(
                  argument.value
              )
          else:
              values.append(
                  argument
              )

      print(*values)

      return UndefinedValue()
    def evaluate(self, node):

        method_name = (
            f"visit_{type(node).__name__}"
        )

        method = getattr(
            self,
            method_name,
            self.no_visit_method
        )

        return method(node)

    def no_visit_method(self, node):

        raise Exception(
            f"No visit method for "
            f"{type(node).__name__}"
        )
    
    def visit_ProgramNode(self, node):

      result = UndefinedValue()

      for statement in node.body:
          result = self.evaluate(
              statement
          )

      return result
    def visit_NumberNode(self, node):

      return NumberValue(
          node.token.value
      )
    def visit_VariableDeclarationNode(
      self,
      node
  ):

      value = self.evaluate(
          node.value
      )

      self.environment.define(
          node.identifier.token.value,
          value
      )

      return value
    
    def visit_ExpressionStatementNode(
      self,
      node
    ):

      return self.evaluate(
          node.expression
      )

    def visit_IdentifierNode(
        self,
        node
    ):

        return self.environment.lookup(
            node.token.value
        )
    def visit_BinaryExpressionNode(self, node):

        left = self.evaluate(
            node.left
        )

        right = self.evaluate(
            node.right
        )

        if node.operator.type == T_PLUS:
            return NumberValue(
                left.value + right.value
            )

        if node.operator.type == T_MINUS:
            return NumberValue(
                left.value - right.value
            )

        if node.operator.type == T_MUL:
            return NumberValue(
                left.value * right.value
            )

        if node.operator.type == T_DIV:
            return NumberValue(
                left.value / right.value
            )

        if node.operator.type == T_MOD:
            return NumberValue(
                left.value % right.value
            )

        if node.operator.type == T_GT:
            return BooleanValue(
                left.value > right.value
            )

        if node.operator.type == T_LT:
            return BooleanValue(
                left.value < right.value
            )

        if node.operator.type == T_GTE:
            return BooleanValue(
                left.value >= right.value
            )

        if node.operator.type == T_LTE:
            return BooleanValue(
                left.value <= right.value
            )

        if node.operator.type == T_EQ:
            return BooleanValue(
                left.value == right.value
            )

        if node.operator.type == T_NEQ:
            return BooleanValue(
                left.value != right.value
            )

        raise Exception(
            f"Unsupported operator {node.operator.type}"
        )
    def visit_AssignmentExpressionNode(self, node):
      value = self.evaluate(
          node.right
      )

      self.environment.assign(
          node.left.token.value,
          value
      )

      return value
    def visit_StringNode(self, node):
      return StringValue(
          node.token.value
      )
    def visit_BooleanNode(self, node):
      return BooleanValue(
          node.token.value
      )
    def visit_NullNode(self, node):
      return NullValue()
    def visit_UndefinedNode(self, node):
      return UndefinedValue()
    
    def visit_BlockStatementNode(
      self,
      node
  ):

      result = UndefinedValue()

      for statement in node.body:

          result = self.evaluate(
              statement
          )

      return result
    
    def visit_IfStatementNode(
      self,
      node
  ):

      condition = self.evaluate(
          node.condition
      )

      if condition.value:

          return self.evaluate(
              node.consequent
          )

      if node.alternate:

          return self.evaluate(
              node.alternate
          )

      return UndefinedValue()

    def visit_BreakStatementNode(self, node):
        raise BreakException()

    def visit_ContinueStatementNode(self, node):
        raise ContinueException()

    def visit_WhileStatementNode(
        self,
        node
    ):

        result = UndefinedValue()

        while self.evaluate(
            node.condition
        ).value:

            try:

                result = self.evaluate(
                    node.body
                )

            except ContinueException:
                continue

            except BreakException:
                break

        return result

    def visit_DoWhileStatementNode(
        self,
        node
    ):

        result = UndefinedValue()

        while True:

            try:

                result = self.evaluate(
                    node.body
                )

            except ContinueException:
                pass

            except BreakException:
                break

            if not self.evaluate(
                node.condition
            ).value:
                break

        return result

    def visit_ForStatementNode(
        self,
        node
    ):

        result = UndefinedValue()

        if node.initializer:
            self.evaluate(
                node.initializer
            )

        while True:

            if (
                node.condition
                and
                not self.evaluate(
                    node.condition
                ).value
            ):
                break

            try:

                result = self.evaluate(
                    node.body
                )

            except ContinueException:

                if node.update:
                    self.evaluate(
                        node.update
                    )

                continue

            except BreakException:
                break

            if node.update:
                self.evaluate(
                    node.update
                )

        return result
    
    def visit_ArrayNode(self, node):

        elements = []

        for element in node.elements:

            elements.append(
                self.evaluate(element)
            )

        return ArrayValue(
            elements
        )

    def visit_ObjectNode(self, node):

        properties = {}

        for property in node.properties:

            key = property.key.token.value

            value = self.evaluate(
                property.value
            )

            properties[key] = value

        return ObjectValue(
            properties
        )

    def visit_MemberExpressionNode(
        self,
        node
    ):

        object_value = self.evaluate(
            node.object
        )

        property_name = (
            node.property.token.value
        )

        return object_value.properties[
            property_name
        ]

    def visit_ComputedMemberExpressionNode(
        self,
        node
    ):

        object_value = self.evaluate(
            node.object
        )

        property_value = self.evaluate(
            node.property
        )

        if isinstance(
            object_value,
            ArrayValue
        ):

            return object_value.elements[
                property_value.value
            ]

        return object_value.properties[
            property_value.value
        ]

    def visit_FunctionDeclarationNode(
        self,
        node
    ):

        function = FunctionValue(
            node.parameters,
            node.body,
            self.environment
        )

        self.environment.define(
            node.name.token.value,
            function
        )

        return function   

    def visit_ReturnStatementNode(
        self,
        node
    ):

        value = self.evaluate(
            node.value
        )

        raise ReturnException(
            value
        )

    def visit_CallExpressionNode(
        self,
        node
    ):

        function = self.evaluate(
            node.callee
        )

        arguments = []

        for argument in node.arguments:

            arguments.append(
                self.evaluate(argument)
            )

        if isinstance(
            function,
            NativeFunctionValue
        ):

            return function.callback(
                arguments
            )

        local_environment = Environment(
            function.environment
        )

        for parameter, argument in zip(
            function.parameters,
            arguments
        ):

            local_environment.define(
                parameter.token.value,
                argument
            )

        previous_environment = (
            self.environment
        )

        self.environment = (
            local_environment
        )

        try:

            self.evaluate(
                function.body
            )

            result = UndefinedValue()

        except ReturnException as return_value:

            result = return_value.value

        self.environment = (
            previous_environment
        )

        return result