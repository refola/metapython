from __future__ import with_statement
import token
import tokenize
from operator import itemgetter
from cStringIO import StringIO

NESTING_OPS = {
    '(':')',
    '{':'}',
    '[':']' }

CLOSING_OPS = set(NESTING_OPS.values())

KEYWORDS = [
    'for', 'while', 'if', 'else', 'import', 'from' ]

SUITE_HEADERS = set([
        'for', 'while', 'if', 'else',
        'try', 'except', 'class', 'def',
        'defcode'])

class GenSym(object):

    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return '_mpy_%d' % self.count

gensym = GenSym()

class Builder(object):
    '''Helper class for building up blocks of code.

    A builder maintains a stack of Block objects called the statement stack.
    This stack can be pushed & popped, and the top of the stack can have new
    statements appended to it.
    '''
    def __init__(self):
        self.stack = [ ]

    @property
    def top(self):
        '''Return the top of the statement stack'''
        return self.stack[-1]

    def append(self, stmt, glbls, lcls):
        '''Append a statement to the current top of the statement stack'''
        try:
            self.top.append(stmt, glbls, lcls)
        except NameError, ne:
            print ne
            print 'Exception in %s' % stmt
            import pdb; pdb.set_trace()
            raise

    def push(self):
        '''Push an empty block onto the statement stack.'''
        self.stack.append(Block())

    def pop(self):
        '''Pop and return the block on top of the statement stack.'''
        return self.stack.pop()

    def append_suite(self, header, glbls, lcls):
        '''Create a suite based on the header line given and the block on the top
        of the stack (which will be popped and used as the body).  Then append
        the newly created suite to the new top of the statement stack.
        '''
        if isinstance(header, basestring):
            header = list(tokens_from_string(header))
        # print 'old header: %r' % string_from_tokens(header, True)
        new_header = list(expand_macros(header, glbls, lcls))
        # print 'new header: %r' % string_from_tokens(new_header, True)
        suite = Suite(new_header, self.pop())
        self.append(suite, glbls, lcls)

    def q(self, code, inline=True):
        '''Quote a code fragment and parse it.'''
        return parse_string(str(code), inline=inline)

def string_from_tokens(toks, inline=False):
    '''Build a string from a sequence of tokens.  This is a "better" version of
    `tokenize.untokenize`, as it verifies that INDENT and DEDENT tokens are
    appropriately converted to valid Python code (which tokenize.untokenize can
    fail to do correctly.
    '''
    def reindent():
        indent = ['']
        for tok in toks:
            if tok.match(token.INDENT):
                cur_indent = indent[-1]
                if (tok.value.startswith(cur_indent)
                    and len(tok.value) > indent):
                    cur_indent = tok.value
                    yield tok
                else:
                    cur_indent += '    '
                    tok = Token.make(
                        tok.token, cur_indent,
                        tok.begin, tok.end, tok.line)
                indent.append(cur_indent)
                yield tok
            elif tok.match(token.DEDENT):
                if len(indent) > 1:
                    indent.pop()
                    if tok.value != indent[-1]:
                        tok = Token.make(
                            tok.token, indent[-1],
                            tok.begin, tok.end, tok.line)
                    yield tok
            else:
                yield tok
    toks = list(reindent())
    if inline:
        while toks and toks[-1].match(token.NEWLINE):
            toks.pop()
    return tokenize.untokenize(toks)

def tokens_from_string(s):
    '''Convert a string to a stream of tokens'''
    if not isinstance(s, basestring):
        import pdb; pdb.set_trace()
    readline = StringIO(s).readline
    strm = ( Token.make(*py_tok)
             for py_tok in tokenize.generate_tokens(readline))
    return strm

def tokens_from_file(fp):
    '''Convert a file to a stream of tokens.'''
    strm = ( Token.make(*py_tok)
             for py_tok in tokenize.generate_tokens(fp.readline))
    return strm

def parse_file(fn, namespace=None):
    '''Convert a file to a Block of statements.'''
    def gen():
        with open(fn) as fp:
            for tok in tokens_from_file(fp):
                yield tok
    return parse_stream(gen(), filename=fn)

def parse_string(s, filename='<string>', inline=False):
    '''Convert a string to a Block of statements.'''
    return parse_stream(tokens_from_string(s), filename=filename, inline=inline)

def expand_macros(tokenstream, glbls=None, lcls=None, filename=None):
    '''Expand $-escapes in a token stream'''
    inp = iter(tokenstream)
    while True:
        t = inp.next()
        while t.match(token.ERRORTOKEN, '$'):
            expr_toks = list(_read_expr(inp))
            expr_toks, t = expr_toks[:-1], expr_toks[-1]
            if t.match(token.OP, ':') and not expr_toks:
                # Read a macro suite and execute it
                t = inp.next()
                if t.match(token.NEWLINE):
                    suite = list(_read_indented_block(inp))
                    prologue, suite, epilogue = \
                        suite[0], suite[1:-1], suite[-1]
                else:
                    suite = [t] + list(_read_to_newline(inp))
                exec string_from_tokens(suite) in glbls, lcls
                t = inp.next()
                continue
            if expr_toks[0].match(token.NAME, *KEYWORDS):
                yield t
                for tok in expr_toks:
                    yield tok
                continue
            expanded_expr_toks = expand_inline_codequotes(
                iter(expr_toks), filename)
            expanded_expr_toks = expand_macros(
                expanded_expr_toks, glbls, lcls, filename)
            block = parse_stream(expanded_expr_toks, filename)
            result = block.eval(glbls, lcls)
            if hasattr(result, 'as_python'):
                result = result.as_python(True)
            for tok in parse_string(str(result)):
                yield tok
        yield t

def expand_inline_codequotes(inp, filename='<string>'):
    '''Expand ?-escapes in a token stream'''
    while True:
        t = inp.next()
        while t.match(token.ERRORTOKEN, '?'):
            quoted_expr = list(_read_expr(inp))
            quoted_expr, t = quoted_expr[:-1], quoted_expr[-1]
            quoted_expr_str = string_from_tokens(quoted_expr)
            text = ('_mpy.q(%r, inline=True)'
                    % quoted_expr_str)
            for tt in parse_string(text, filename): yield tt
        yield t

def parse_stream(tokenstream, filename='<string>', inline=False):
    '''Convert a stream of tokens into a Block of statements.'''
    def gen():
        cur_line = []
        inp = iter(tokenstream)
        try:
            while True:
                t = inp.next()
                if (t.match(token.ERRORTOKEN, ' ')
                    or t.match(token.ENDMARKER)
                    or t.tok_name == 'NL'):
                    continue
                cur_line.append(t)
                if t.match(token.NEWLINE):
                    yield Stmt(cur_line)
                    cur_line = []
                elif t.match(token.OP, ':'):
                    # The cur_line is (possibly) a header line of a Suite
                    if not _is_suite_header(cur_line):
                        continue
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
    block = Block(list(gen()))
    if inline:
        assert len(block.statements) == 1, 'Illegal multiline short-quote (?)'
        return block.statements[0]
    return block
            
class Stmt(object):
    '''Base statement class'''

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
        return self.as_python(True)
    #return 'Stmt(%r)' % self.tokens

    def __str__(self):
        return self.as_python(True)

    def as_python(self, inline=False):
        return string_from_tokens(self, inline)

    def expand_defcode_blocks(self):
        def gen_toks():
            inp = iter(self)
            while True:
                tok = inp.next()
                if tok.match(token.ERRORTOKEN, '?'):
                    expr = list(_read_expr(inp))
                    expr_end = expr[-1]
                    text = '_mpy.q(%r)' % string_from_tokens(expr[:-1])
                    for tok in parse_string(text):
                        yield tok
                    yield expr_end
                else:
                    yield tok
        for stmt in parse_stream(gen_toks()).statements:
            yield stmt

    def quote(self):
        toks = list(self)
        if (toks[0].match(token.ERRORTOKEN, '$')
            and len(toks) > 1
            and toks[1].match(token.NAME, *KEYWORDS)):
                return parse_stream(toks[1:]).one()
        else:
            s_str = self.as_python()
            result = parse_string('_mpy.append(%r, globals(), locals())' % s_str)
            return result

    def append(self, token):
        self.tokens.append(token)

    def __eq__(self, other):
        return list(self) == list(other)

class Suite(Stmt):
    '''A block-type statement, with a header and a body'''

    def __init__(self, header, body, prologue=None, epilogue=None):
        if prologue is None:
            prologue = [ Token.make(token.INDENT, '    ', (0,0), (0,0), '') ]
        if epilogue is None:
            epilogue = [ Token.make(token.DEDENT, '', (0,0), (0,0), '') ]
        if isinstance(header, basestring):
            header = tokens_from_string(header)
        if not header[-1].match(token.NEWLINE):
            header = header + [ Token.make(token.NEWLINE, '\n',
                                           header[-1].end, header[-1].end,
                                           header[-1].line) ]
        self.header, self.body, self.prologue, self.epilogue = \
            header, body, prologue, epilogue
        self.eol = False

    def first(self):
        return self.header[0]

#     def __repr__(self):
#         return 'Suite(%r, %r, %r, %r)' % (
#             self.header, self.body, self.prologue, self.epilogue)

    def __iter__(self):
        for tok in self.header: yield tok
        for tok in self.prologue: yield tok
        for tok in self.body: yield tok
        for tok in self.epilogue: yield tok

    def expand_defcode_blocks(self):
        if self.first().match(token.NAME, 'defcode'):
            code_name = self.header[1].value
            if self.header[2].match(token.OP, '('):
                args = _read_args(iter(self.header[3:]))
                args = (parse_stream(a).expand_defcode_blocks()
                        for a in args)
                args = (str(a).strip() for a in args)
                args = (repr(a) for a in args)
                omit_names = ','.join(args)
            else:
                import pdb; pdb.set_trace()
                raise SyntaxError, 'Expected arglist'
            block = Block()
            block.append('_mpy.push()', {}, {})
            for stmt in self.body.statements:
                block.append(stmt.quote(), {}, {})
            block.append('%s = _mpy.pop()' % code_name, {}, {})
            block.append('%s = %s.sanitize(globals(), locals(), %s)' % (
                    code_name,
                    code_name,
                    omit_names), {}, {})
            for stmt in block.statements:
                yield stmt
        else:
            expanded_body = self.body.expand_defcode_blocks()
            yield Suite(self.header, expanded_body,
                        self.prologue, self.epilogue)

    def quote(self):
        if self.header[0].match(token.ERRORTOKEN, '$'):
            new_header = self.header[1:]
            if new_header[0].match(token.OP, ':'):
                return self.body
            else:
                new_body = self.body.quote()
                return Suite(
                    new_header, new_body, self.prologue, self.epilogue)
        else:
            result = Block()
            result.append('_mpy.push()', {}, {})
            for stmt in self.body.statements:
                result.append(stmt.quote(), {}, {})
            header = string_from_tokens(self.header, True)
            result.append(
                '_mpy.append_suite(%r, globals(), locals())' % header,
                {}, {})
            return result
        
    def append(self, token):
        self.epilogue.append(token)
        
class Block(object):
    '''A sequence of statements'''

    def __init__(self, statements=None):
        if statements is None: statements = []
        self.statements = statements

    def sanitize(self, glbls, lcls, *omit_names):
        '''Ask this block's builder to sanitize this block,
        omitting the listed names'''
        omit_names = [
            str(eval(n, glbls, lcls)).strip()
             for n in omit_names ]
        myfun = Suite(
            list(parse_string('def _():')),
            self,
            [ Token.make(token.INDENT, '    ', (0,0), (0,0), '') ],
            [ Token.make(token.DEDENT, '    ', (0,0), (0,0), ''),
              Token.make(token.NEWLINE, '\n', (0,0), (0,0), '\n')])
        ns = {}
        exec myfun.as_python() in ns
        code = ns['_'].func_code
        names = set(code.co_varnames)
        for on in omit_names:
            try:
                names.remove(on)
            except KeyError:
                pass
        newnames = dict((n, gensym()) for n in names)
        result = self.replace_names(**newnames)
#         print 'Santize result:'
#         print self.as_python()
#         print '==='
#         print result.as_python()
        return result

    def replace_names(self, **newnames):
        '''Replace the NAMEs in this block according to the newnames mapping.'''
        def translate():
            for tok in self:
                if tok.match(token.NAME):
                    yield tok.replace(
                        value=newnames.get(tok.value, tok.value))
                elif tok.match(token.ENDMARKER):
                    continue
                else:
                    yield tok
        return parse_stream(translate())

    def __iter__(self):
        for s in self.statements:
            for t in s:
                yield t

#     def __repr__(self):
#         return 'Block(%r)' % self.statements

    def __str__(self):
        return self.as_python(True)

    def __repr__(self):
        return self.as_python(True)

    def as_python(self, inline=False):
        text = string_from_tokens(self, inline)
        if not inline and (not text or text[-1] != '\n'):
            text += '\n'
        return text

    def expand_defcode_blocks(self):
        result = Block()
        for s in self.statements:
            result.append(Block(list(s.expand_defcode_blocks())), {}, {})
        return result

    def quote(self, code_name=None):
        '''Expand the code in the block under the assumption that
        it is part of a defcode: block'''
        block = Block()
        if code_name:
            block.append('_mpy.push()', {}, {})
        for stmt in self.statements:
            block.append(stmt.quote(), {}, {})
        if code_name is not None:
            block.append('%s = _mpy.pop()' % code_name, {}, {})
        return block

    def indent(self):
        tokens = [ t.indent() for t in self ]
        return parse_stream(tokens)
        
    def append(self, statement, glbls, lcls):
        if self.statements:
            last_stmt = self.statements[-1]
            if not last_stmt.eol:
                last_stmt.append(Token.make(token.NEWLINE, '\n', (0,0), (0,0), ''))
                last_stmt.eol = True
        if isinstance(statement, basestring):
            toks = tokens_from_string(statement)
            toks = list(expand_macros(toks, glbls, lcls))
            statement = parse_stream(toks)
        if isinstance(statement, Block):
            for ss in statement.statements:
                self.append(ss, glbls, lcls)
        else:
            self.statements.append(statement)

    def one(self):
        if len(self.statements) != 1:
            raise SyntaxError, 'Expected a single statement'
        return self.statements[0]

    def expand(self, glbls=None, lcls=None):
        quoted = self.quote()
        if glbls == lcls == None:
            _mpy = Builder()
            glbls = lcls = dict(_mpy=_mpy)
        else:
            _mpy = glbls.get('_mpy', lcls.get('_mpy'))
        _mpy.push()
        quoted.exec_(glbls, lcls)
        return _mpy.pop()

    def eval(self, glbls, lcls):
        try:
            return eval(self.as_python(True), glbls, lcls)
        except NameError, ne:
            print self
            print ne
            import pdb; pdb.set_trace()
            raise
        except TypeError, te:
            print te
            import pdb; pdb.set_trace()
            raise
        except SyntaxError, se:
            print se.text
            print '-' * (se.offset-1) + '^'
            print se
            import pdb; pdb.set_trace()
            raise
            

    def exec_(self, glbls, lcls):
        text = self.as_python()
        try:
            exec text in glbls, lcls
        except SyntaxError, se:
            print se.text
            print '-' * (se.offset-1) + '^'
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
            raise

    def __eq__(self, other):
        return list(self) == list(other)


class Token(tuple):
    '''Thin wrapper around tuple to allow access to the token.generate_tokens
    results by name
    '''
    __slots__ = ()
    token=property(itemgetter(0))
    value=property(itemgetter(1))
    begin=property(itemgetter(2))
    end=property(itemgetter(3))
    line=property(itemgetter(4))
    field_names = (
        'token', 'value', 'begin', 'end', 'line')

    @classmethod
    def make(klass, token, value, begin, end, line):
        return klass((token, value, begin, end, line))

    def replace(self, **kwds):
        result = self.make(*map(kwds.pop, self.field_names, self))
        if kwds:
            raise ValueError('Got unexpected field names: %r'
                             % kwds.keys())
        return result

    @property
    def tok_name(self):
        return token.tok_name[self.token]

    def __repr__(self):
        t = ('_mpy.token.%s' % self.tok_name,) +  self[1:]
        if len(self) != 5:
            print tuple(self)
            import pdb; pdb.set_trace()
        return '_mpy.Token.make(%s,%r,%r,%r,%r)' % t

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
            return Token.make(
                self.token, self.value + '    ',
                self.begin, self.end, self.line)
        else:
            return self

def _read_indented_block(inp):
    '''Generator that reads and yields tokens in an INDENT...DEDENT block.
    Handles nested indents and yields the INDENT and the DEDENT tokens.
    '''
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
    '''Generator that reads (and yields) tokens until a NEWLINE is encountered.
    Yields the terminating NEWLINE.
    '''
    while True:
        tok = inp.next()
        yield tok
        if tok.match(token.NEWLINE): break

def _read_expr(tokenstream, *expr_closing_ops):
    '''Read an expression from a token stream.  The expression
    ends when one of the expr_closing_ops operators is encountered.'''
    first_token = None
    while True:
        try:
            t = tokenstream.next()
        except StopIteration:
            yield Token.make(token.ENDMARKER, '', (0,0), (0,0), '')
            break
        if first_token is None and t.match(token.OP, '<'):
            for tok in _read_nested(tokenstream, '>'):
                if not tok.match(token.OP, '>'):
                    yield tok
                else:
                    yield Token.make(token.ERRORTOKEN, ' ',
                                     tok.begin, tok.end, tok.line)
            break
        first_token = t
        yield t
        if expr_closing_ops and t.match(token.OP, *expr_closing_ops):
            break
        elif t.match(token.OP, *NESTING_OPS.keys()):
            for tok in _read_nested(tokenstream, NESTING_OPS[t.value]):
                yield tok
        elif t.match(token.OP, CLOSING_OPS):
            break
        elif t.match(token.NAME):
            continue
        elif t.match(token.NUMBER):
            continue
        elif expr_closing_ops and t.match(token.OP, ',', ':'):
            continue
        else:
            break

def _read_args(tokenstream):
    while True:
        arg = list(_read_expr(tokenstream, ',', ')'))
        if len(arg) == 1 and arg[0].match(token.ERRORTOKEN, '?'):
            arg += list(_read_expr(tokenstream, ',', ')'))
        if len(arg) > 1:
            yield arg[:-1]
        if arg[-1].match(token.OP, ')'): break

def _read_nested(tokenstream, *closing_ops):
    '''Read a possibly nested expression.  The closing_ops are the operators
    which can close the expression.'''
    while True:
        t = tokenstream.next()
        yield t
        if t.match(token.OP, *closing_ops):
            break
        elif t.match(token.OP, *NESTING_OPS.keys()):
            for tok in _read_nested(tokenstream, NESTING_OPS[t.value]):
                yield tok

def _is_suite_header(cur_line):
    '''Determine whether the given list of tokens constitutes a suite header.
    Suite headers begin with one of the SUITE_HEADERS tokens and contain a
    colon.  (Though I believe the check for a colon is superfluous.)
    '''
    for first_tok in cur_line:
        if first_tok.token >= token.ERRORTOKEN:
            continue
        break
    if first_tok.match(token.NAME, *SUITE_HEADERS):
        return True
    elif first_tok.match(token.OP, ':'):
        return True
    return False
