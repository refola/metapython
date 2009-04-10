import token
import tokenize

class Code(object):
    '''Code object for MetaPython.  (A Code object is really just a sequence of
    tokens, but it's nice to have the class for isinstance() testing.)'''

    def __init__(self, *tokens):
        self.tokens = tokens

    def __repr__(self):
        '''Return the Python text corresponding to this Code object'''
        return tokenize.untokenize(self.tokens).rstrip()

    def __iter__(self):
        return iter(self.tokens)

    def eval(self):
        '''Force evaluation of a code expression'''
        return eval(repr(self))

    def extend(self, other):
        '''Extend the current code object with a newline and the tokens
        from the other sequence.'''
        self.tokens += (token.NEWLINE, '\n', (0,0), (0,0), None),
        self.tokens += tuple(other)
            
