class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.variables = {}

    def define(self, name, value):
        self.variables[name] = value
        return value

    def lookup(self, name):

        if name in self.variables:
            return self.variables[name]

        if self.parent:
            return self.parent.lookup(name)

        raise Exception(
            f"Variable '{name}' is not defined"
        )

    def assign(self, name, value):

        if name in self.variables:
            self.variables[name] = value
            return value

        if self.parent:
            return self.parent.assign(
                name,
                value
            )

        raise Exception(
            f"Variable '{name}' is not defined"
        )