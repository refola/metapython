class Builder(object):
    '''Helper class for building up blocks of code'''
    def __init__(self):
        self.stack = [ ]

    @property
    def top(self):
        return self.stack[-1]

    def append(self, stmt):
        self.top.append(stmt)

    def push(self, namespace=None):
        from parse import Block
        if namespace is None and self.stack:
            namespace = self.top.namespace
        self.stack.append(Block(namespace=namespace))

    def pop(self):
        return self.stack.pop()

    def suite(self, header):
        from parse import Suite
        return Suite(header, self.pop())
