import token
import tokenize
from operator import itemgetter
from cStringIO import StringIO

from core import _read_suite

class Suite(object):

    def __init__(self, tokenstream, filename='<string>'):
        self.tokens = map(Token, tokenstream)
        self.filename = filename

    @classmethod
    def from_string(klass, s):
        tokenstream = tokenize.generate_tokens(
            StringIO(s).readline)
        return klass(tokenstream)

    def __iter__(self):
        for tok in self.tokens: yield tok

    def as_str(self):
        return tokenize.untokenize(self.tokens)

    def expand_quoted_code(self):
        inp = iter(self.tokens)
        def gen():
            while True:
                tok = inp.next()
                if tok.match(token.NAME, 'defcode'):
                    tok_name = inp.next()
                    tok_name.assertMatch(token.NAME)
                    inp.next().assertMatch(token.OP, ':')
                    suite = Suite(_read_suite(
                        inp, keep_header=False, colon_already_read=True))
                    suite = suite.expand_defcode(tok_name.value)
                    for tok in suite: yield tok
                else:
                    yield tok
        return Suite(gen())

    def expand_defcode(self, name):
        inp = iter(self.tokens)
        def gen():
            for tok in Suite.from_string(
                '%s = Suite()' % name):
                yield tok
            while True:
                tok = inp.next()
                if tok.match(token.ERRTOK, '$'):
                    tok = inp.next()
                    if tok.match(token.NAME, 'while', 'for', 'if', 'else'):
                        yield tok
                        while True:
                            tt = inp.next()
                            yield tt
                            if tt.match(token.OP, ':'):
                                
                        for tt in _read_suite(inp, keep_header=True):
                            yield Token(tt)
                    else:
                        for tt in _read_expr(inp):
                            yield Token(tt)
                else:
                    
                    
                        
                            

class Token(tuple):
    __slots__ = ()
    token=property(itemgetter(0))
    value=property(itemgetter(1))
    begin=property(itemgetter(2))
    end=property(itemgetter(3))
    line=property(itemgetter(4))

    @property
    def tok_name(self):
        return token.tok_name[self.token]

    def match(self, tok, *values):
        if self.token != tok: return False
        if not values: return True
        for v in values:
            if self.value == v: return True
        else:
            return False

    def assertMatch(self, tok, *values, **kw):
        filename = kw.pop('filename', '<string>')
        assert not kw, 'Unknown kw args: %r' % kw
        if not self.match(tok, *values):
            raise SyntaxError(
                'Expected %s, found %s' % ((tok,values), self),
                (filename, self.begin[0], self.begin[1], self.line))

