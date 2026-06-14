class RuntimeValue:
    pass


class NumberValue(RuntimeValue):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"NumberValue({self.value})"


class StringValue(RuntimeValue):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'StringValue("{self.value}")'


class BooleanValue(RuntimeValue):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"BooleanValue({self.value})"


class NullValue(RuntimeValue):
    def __repr__(self):
        return "NullValue()"


class UndefinedValue(RuntimeValue):
    def __repr__(self):
        return "UndefinedValue()"
    
class ArrayValue(RuntimeValue):
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        return f"ArrayValue({self.elements})"


class ObjectValue(RuntimeValue):
    def __init__(self, properties):
        self.properties = properties

    def __repr__(self):
        return f"ObjectValue({self.properties})"
    

class FunctionValue(RuntimeValue):

    def __init__(
        self,
        parameters,
        body,
        environment
    ):
        self.parameters = parameters
        self.body = body
        self.environment = environment

    def __repr__(self):
        return "FunctionValue()"
    
class NativeFunctionValue(RuntimeValue):

    def __init__(self, callback):
        self.callback = callback

    def __repr__(self):
        return "NativeFunctionValue()"