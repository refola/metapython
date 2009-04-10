from __future__ import with_statement
import token
import tokenize
from operator import itemgetter
from cStringIO import StringIO

import builder

NESTING_OPS = {
    '(':')',
    '{':'}',
    '[':']' }

CLOSING_OPS = set(NESTING_OPS.values())

KEYWORDS = [
    'for', 'while', 'if', 'else', 'import', 'from' ]

def tokens_from_string(s):
    if not isinstance(s, basestring):
        import pdb; pdb.set_trace()
    readline = StringIO(s).readline
    strm = ( Token(py_tok) for py_tok in tokenize.generate_tokens(readline))
    return strm

def tokens_from_file(fp):
    strm = ( Token(py_tok) for py_tok in tokenize.generate_tokens(fp.readline))
    return strm

def parse_file(fn, namespace=None):
    def gen():
        with open(fn) as fp:
            for tok in tokens_from_file(fp):
                yield tok
    return parse_stream(gen(), filename=fn, namespace=namespace)

def parse_string(s, filename='<string>', namespace=None):
    return parse_stream(tokens_from_string(s), filename=filename, namespace=namespace)

def expand_macros(tokenstream, filename='<string>', namespace=None):
    inp = iter(tokenstream)
    while True:
        t = inp.next()
        while t.match(token.ERRORTOKEN, '$'):
            expr_toks = list(_read_expr(inp))
            expr_toks, t = expr_toks[:-1], expr_toks[-1]
            if expr_toks[0].match(token.NAME, *KEYWORDS):
                yield t
                for tok in expr_toks:
                    yield tok
                break
            expanded_expr_toks = expand_inline_codequotes(iter(expr_toks), filename)
            block = parse_stream(expanded_expr_toks, filename)
            block.namespace = namespace
            result = block.eval()
            if hasattr(result, 'as_python'):
                result = result.as_python()
            for tok in parse_string(str(result)):
                yield tok
        yield t

def expand_inline_codequotes(inp, filename):
    while True:
        t = inp.next()
        if t.match(token.ERRORTOKEN, '?'):
            quoted_expr = _read_expr(inp)
            text = '_mpy.parse_string(%r)' % quoted_expr.as_python()
            for tt in parse_string(text, filename): yield tt
        else:
            yield t

def parse_stream(tokenstream, filename='<string>', namespace=None):
    def gen():
        cur_line = []
        inp = iter(tokenstream)
        try:
            while True:
                t = inp.next()
                if t.match(token.ERRORTOKEN, ' '):
                    continue
                if not t.match(token.ENDMARKER):
                    cur_line.append(t)
                if t.match(token.NEWLINE):
                    yield Stmt(cur_line)
                    cur_line = []
                elif t.match(token.OP, ':'):
                    # The cur_line is a header line of a Suite
                    t = inp.next()
                    if t.match(token.NEWLINE):
                        # Indented block
                        cur_line.append(t)
                        tokens = list(_read_indented_block(inp))
                        prologue, tokens, epilogue = \
                            tokens[0], tokens[1:-1], tokens[-1]
                        lines = parse_stream(tokens, filename)
                        yield Suite(cur_line, lines, [prologue], [epilogue])
                        cur_line = []
                    else:
                        # Inline block
                        tokens = [ t ] + list(_read_to_newline(inp))
                        lines = parse_stream(tokens, filename)
                        yield Suite(cur_line, lines)
                        cur_line = []
                elif t.match(token.ENDMARKER):
                    if cur_line: yield Stmt(cur_line)
                    cur_line = []
        except StopIteration:
            if cur_line: yield Stmt(cur_line)
    return Block(list(gen()), namespace=namespace)
            
class Stmt(object):

    def __init__(self, tokens):
        self.tokens = tokens
        if self.tokens[-1].match(token.NEWLINE):
            self.eol = True
        else:
            self.eol = False

    def __iter__(self):
        for t in self.tokens:
            yield t

    def first(self):
        return self.tokens[0]

    def __repr__(self):
        return 'Stmt(%r)' % self.tokens

    def as_python(self):
        return tokenize.untokenize(self)

    def expand_defcode_blocks(self):
        yield self

    def quote(self):
        toks = list(self)
        if False and toks[0].match(token.ERRORTOKEN, '$'):
            return parse_stream(toks[1:]).one()
        else:
            s_str = self.as_python()
            result = parse_string('_mpy.append(%r)' % s_str)
            return result

    def append(self, token):
        self.tokens.append(token)

    def __eq__(self, other):
        return list(self) == list(other)

class Suite(Stmt):

    def __init__(self, header, body, prologue=None, epilogue=None):
        if prologue is None:
            prologue = [ Token((token.INDENT, '    ', (0,0), (0,0))) ]
        if epilogue is None:
            epilogue = [ Token((token.DEDENT, '', (0,0), (0,0))) ]
        if isinstance(header, basestring):
            header = tokens_from_string(header)
        self.header, self.body, self.prologue, self.epilogue = \
            header, body, prologue, epilogue
        self.eol = False

    def first(self):
        return self.header[0]

    def __repr__(self):
        return 'Suite(%r, %r, %r, %r)' % (
            self.header, self.body, self.prologue, self.epilogue)

    def __iter__(self):
        for tok in self.header: yield tok
        for tok in self.prologue: yield tok
        for tok in self.body: yield tok
        for tok in self.epilogue: yield tok

    def expand_defcode_blocks(self):
        if self.first().match(token.NAME, 'defcode'):
            code_name = self.header[1].value
            block = parse_string('_mpy.push(locals())')
            for stmt in self.body.statements:
                block.append(stmt.quote())
            block.append(parse_string('%s = _mpy.pop()' % code_name))
            for stmt in block.statements:
                yield stmt
        else:
            expanded_body = self.body.expand_defcode_blocks()
            yield Suite(self.header, expanded_body,
                        self.prologue, self.epilogue)

    def quote(self):
        if self.header[0].match(token.ERRORTOKEN, '$'):
            new_header = self.header[1:]
            if len(new_header) == 1:
                return self.body
            else:
                new_body = self.body.quote()
                return Suite(
                    new_header, new_body, self.prologue, self.epilogue)
        else:
            result = Block()
            result.append('_mpy.push()')
            for stmt in self.body.statements:
                result.append(stmt.quote())
            header = tokenize.untokenize(self.header)
            result.append('_mpy.append(_mpy.suite(%r))' % header)
            return result
        
    def append(self, token):
        self.epilogue.append(token)
        
class Block(object):

    def __init__(self, statements=None, namespace=None):
        if statements is None: statements = []
        self.statements = statements
        self.namespace = namespace

    def __iter__(self):
        for s in self.statements:
            for t in s:
                yield t

    def __repr__(self):
        return 'Block(%r)' % self.statements

    def as_python(self):
        text = tokenize.untokenize(self)
        if text[-1] != '\n':
            text += '\n'
        return text

    def expand_defcode_blocks(self):
        result = Block(namespace=self.namespace)
        for s in self.statements:
            result.append(Block(list(s.expand_defcode_blocks())))
        return result

    def quote(self, code_name=None):
        '''Expand the code in the block under the assumption that
        it is part of a defcode: block'''
        block = Block()
        if code_name:
            block.append('_mpy.push()')
        for stmt in self.statements:
            block.append(stmt.quote())
        if code_name is not None:
            block.append('%s = _mpy.pop()' % code_name)
        return block

    def indent(self):
        tokens = [ t.indent() for t in self ]
        return parse_stream(tokens)
        
    def append(self, statement):
        if self.statements:
            last_stmt = self.statements[-1]
            if not last_stmt.eol:
                last_stmt.append(Token((token.NEWLINE, '\n', (0,0), (0,0), '')))
                last_stmt.eol = True
        if isinstance(statement, basestring):
            toks = tokens_from_string(statement)
            toks = list(expand_macros(toks, namespace=self.namespace))
            statement = parse_stream(toks)
        if isinstance(statement, Block):
            for ss in statement.statements:
                self.append(ss)
        else:
            self.statements.append(statement)

    def one(self):
        if len(self.statements) != 1:
            raise SyntaxError, 'Expected a single statement'
        return self.statements[0]

    def expand(self):
        quoted = self.quote()
        _mpy = builder.Builder()
        ns = dict(_mpy=_mpy)
        quoted.namespace = ns
        _mpy.push(ns)
        quoted.exec_()
        return _mpy.pop()

    def eval(self):
        return eval(self.as_python(), self.namespace)

    def exec_(self):
        try:
            exec self.as_python() in self.namespace
        except SyntaxError, se:
            print se
            import pdb; pdb.set_trace()
            raise
        except tokenize.TokenError, te:
            print te
            print self.as_python()
            import pdb; pdb.set_trace()
            raise
        except Exception,  ex:
            print ex
            print self.as_python()
            import pdb; pdb.set_trace()

    def __eq__(self, other):
        return list(self) == list(other)


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

    def __repr__(self):
        t = ('_mpy.token.%s' % self.tok_name,) +  self[1:]
        return '_mpy.Token((%s,%r,%r,%r,%r))' % t

    def match(self, tok, *values):
        if self.token != tok: return False
        if not values: return True
        return self.value in values

    def assertMatch(self, tok, *values, **kw):
        filename = kw.pop('filename', '<string>')
        assert not kw, 'Unknown kw args: %r' % kw
        if not self.match(tok, *values):
            raise SyntaxError(
                'Expected %s, found %s' % ((token.tok_name[tok],values), self),
                (filename, self.begin[0], self.begin[1], self.line))

    def __eq__(self, other):
        if self.token != other.token: return False
        if self.token in (token.INDENT, token.DEDENT): return True
        return self.value == other.value

    def indent(self):
        if self.match(token.INDENT):
            return Token((
                    self.token, self.value + '    ',
                    self.begin, self.end, self.line))
        else:
            return self

def _read_indented_block(inp):
    while True:
        tok = inp.next()
        yield tok
        if tok.match(token.INDENT): break
    depth = 1
    while depth:
        tok = inp.next()
        yield tok
        if tok.match(token.DEDENT):
            depth -= 1
        elif tok.match(token.INDENT):
            depth += 1

def _read_to_newline(inp):
    while True:
        tok = inp.next()
        yield tok
        if tok.match(token.NEWLINE): break

def _read_expr(tokenstream, *expr_closing_ops):
    '''Read an expression from a token stream.  The expression
    ends when one of the expr_closing_ops operators is encountered.'''
    first_token = None
    while True:
        t = tokenstream.next()
        if first_token is None and t.match(token.OP, '<'):
            for tok in _read_nested(tokenstream, '>'):
                yield tok
            break
        first_token = t
        yield t
        if t.match(token.OP, expr_closing_ops):
            break
        elif t.match(token.OP, NESTING_OPS.keys()):
            for tok in _read_nested(tokenstream, NESTING_OPS[t.value]):
                yield tok
        elif t.match(token.OP, CLOSING_OPS):
            break
        elif t.match(token.NAME):
            continue
        else:
            break

def _read_nested(tokenstream, *closing_ops):
    '''Read a possibly nested expression.  The closing_ops are the operators
    which can close the expression.'''
    while True:
        t = tokenstream.next()
        yield t
        if t.match(token.OP, *closing_ops):
            break
        elif t.match(token.OP, NESTING_OPS.keys()):
            for tok in _read_nested(tokenstream, NESTING_OPS[t.value]):
                yield tok

