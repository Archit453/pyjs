"""Call frame model for the PyJS VM.

The value stack is a single shared list. A frame's locals/args live between
`base` and the top. Per the frozen call protocol, the stack layout for a call
is:

    [ callee, this, arg0, arg1, ... argN-1, <reserved locals> ]

`base` points at arg0. Therefore:
    frame.this   = value_stack[base - 1]
    callee slot  = value_stack[base - 2]
    local[i]     = value_stack[base + i]

We do not store numeric return addresses; popping a frame resumes the previous
frame at its saved `ip`.
"""


class CallFrame:
    __slots__ = ("closure", "ip", "base", "this")

    def __init__(self, closure, base, this):
        self.closure = closure
        self.ip = 0
        self.base = base
        self.this = this

    @property
    def code(self):
        return self.closure.function.code

    def __repr__(self):
        return f"<CallFrame {self.closure.name} ip={self.ip} base={self.base}>"
