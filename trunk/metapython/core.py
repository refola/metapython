'''Metapython syntax extensions
'''
from __future__ import with_statement
import os
import new
import sys
import token
import tokenize
from cStringIO import StringIO
from itertools import chain

from jinja2 import Template

# from parser import Code
from metapython import parse

NESTING_OPS = {
    '(':')',
    '{':'}',
    '[':']' }

CLOSING_OPS = set(NESTING_OPS.values())

def install_import_hook():
    '''Installs the MetaImporter import hook along sys.meta_path'''
    if MetaImporter not in sys.meta_path:
        sys.meta_path.append(MetaImporter)

class MetaImporter(object):
    '''This is the class responsible for finding .mpy files to import'''

    @staticmethod
    def find_module(fullname, path=None):
        '''This method locates an .mpy file along either
        sys.path or the given path'''
        lastname = fullname.rsplit('.', 1)[-1]
        for d in (path or sys.path):
            mpy = os.path.join(d, lastname + '.mpy')
            if os.path.exists(mpy):
                return MetaLoader(mpy)

class MetaLoader(object):
    '''This is the class responsible for actually loading the .mpy files'''

    def __init__(self, path):
        self.path = path

    def load_module(self, name):
        '''Load a .mpy file from the loader's given path'''
        mod = sys.modules.get(name)
        if mod is None:
            mod = import_file(self.path, name)
            if '.' in name:
                parent_name, child_name = name.rsplit('.', 1)
                setattr(sys.modules[parent_name], child_name, mod)
        return mod

def import_file(fn, name=None):
    '''Import a .mpy file, creating a new module object'''
    if name is None:
        name = os.path.splitext(os.path.basename(fn))[0]
    result = new.module(name)
    sys.modules[name] = result
    try:
        imp, module_doc, module_text = expand_file(fn)
        result.__doc__ = module_doc
        result.__dict__.update(imp.namespace)
        result.__expanded__ = module_text
        return result
    except:
        del sys.modules[name]
        raise

def expand_string(text):
    '''Expand MetaPython text'''
    imp = ImportContext()
    doc, text = imp.expand(StringIO(text).readline)
    return imp, doc, text

def expand_file(fn):
    '''Expand a MetaPython file'''
    imp = ImportContext(fn)
    doc, text = imp.expand(fn)
#     with open(fn) as fp:
#         doc, text = imp.expand(fp.readline)
    return imp, doc, text



class ImportContext(object):
    '''Provides a context to import MetaPython (including local & global
    dicts in which to exec the module code'''

    def __init__(self, filename = '<string>'):
        self.filename = filename
        self._mpy = parse.Builder()
        self.namespace = dict(_mpy=self._mpy)

    def syntax_error(self, message, pos, line):
        '''Helper to raise an appropriate syntax error'''
        raise SyntaxError(message,
                          (self.filename, pos[0], pos[1], line))

    def expand(self, fn):
        '''Token-based macro and code quoting expander'''
        inp = parse.parse_file(fn)
        # Expand the defcode blocks
        inp1 = inp.expand_defcode_blocks()
        # Quote and exec to get the macros expanded
        inp2 = inp1.quote()
        self._mpy.push()
        inp2.exec_(self.namespace, self.namespace)
        inp3 = self._mpy.pop()
        # Exec the module in the namespace
        inp3.exec_(self.namespace, self.namespace)
        first_token = iter(inp3).next()
        if first_token.match(token.STRING):
            doc = first_token.value
        else:
            doc = None
        return doc, inp3.as_python()

    def _expand_macros(self, tokenstream):
        '''Expand import-time macros in a token stream,
        returning the expanded token stream.'''
        while True:
            t,v,b,e,l = tokenstream.next()
            if (t,v) == (token.ERRORTOKEN, '?'):
                for tok in self._expand_escape(b, tokenstream):
                    yield tok
            else:
                yield t,v,b,e,l

    def _expand_escape(self, escape_pos, tokenstream):
        '''Expand a particular ? escape in a tokenstream'''
        t,v,b,e,l = tokenstream.next()
        if (t,v) == (token.OP, ':'):
            # import-time block
            suite = _read_suite(tokenstream, colon_already_read=True)
            text = tokenize.untokenize(suite)
            exec text in self.globals, self.locals
        elif (t,v) == (token.OP, '('):
            expr = list(_read_nested(tokenstream, ')'))[:-1] # drop closing paren
            text = tokenize.untokenize(expr)
            expansion = str(eval(text, self.globals, self.locals))
            for tok in self._expand_macros(
                tokenize.generate_tokens(StringIO(expansion).readline)):
                yield tok
        elif t == token.NAME:
            if v in ('import', 'from'):
                if escape_pos[1] != 0:
                    self.syntax_error(
                        '?import and ?from statements must not be indented',
                        escape_pos, l)
                imp_line = chain(
                    [(t,v,b,e,l)], _read_eol(tokenstream))
                text = tokenize.untokenize(imp_line)
                exec text in self.globals
            else:
                expr = chain([(t,v,b,e,l)], _read_expr(tokenstream, '('))
                expr = list(expr)
                expr, tail = expr[:-1], expr[-1]
                args = _read_args(tokenstream)
                macro_text = tokenize.untokenize(expr)
                macro_callable = eval(macro_text, self.globals, self.locals)
                macro_callable.func_globals.update(self.locals)
                expansion = macro_callable(*args)
                for tok in self._expand_macros(iter(expansion)):
                    yield tok

def _read_eol(tokenstream):
    '''Read tokens till the end of line'''
    t = None
    while t != token.NEWLINE:
        t,v,b,e,l = tokenstream.next()
        yield t,v,b,e,l

def _read_expr(tokenstream, *expr_closing_ops):
    '''Read an expression from a token stream.  The expression
    ends when one of the expr_closing_ops operators is encountered.'''
    while True:
        t,v,b,e,l = tokenstream.next()
        yield t,v,b,e,l
        if t == token.OP:
            if v in expr_closing_ops:
                break
            elif v in NESTING_OPS:
                for tok in _read_nested(tokenstream, NESTING_OPS[v]):
                    yield tok
            elif v in CLOSING_OPS:
                break
            else:
                continue
        elif t == token.NAME:
            continue
        else:
            break

def _expand_quoted_code(tokenstream):
    '''Expand defcode and ${...} constructs in a tokenstream into
    calls to expand_code_template'''
    while True:
        (t,v,b,e,l)  = tokenstream.next()
        if (t,v) == (token.NAME, 'defcode'):
            varname = tokenstream.next()[1]
            tpl_tokens = _read_block(tokenstream)
            # Expand import-time constructs here
            tpl_text = tokenize.untokenize(_read_block(tokenstream))
            new_text = ('%s = __expand_code_template('
                        '%r, globals(),locals())\n'
                        % (varname, tpl_text))
            for tok in tokenize.generate_tokens(StringIO(new_text).readline):
                yield tok
        elif (t,v) == (token.ERRORTOKEN, '?'):
            tt,vv,bb,ee,ll = tokenstream.next()
            if (tt,vv) == (token.OP, '{'):
                expr = list(_read_nested(tokenstream, '}'))[:-1]
                for tok in _expand_quoted_code_expr(expr):
                    yield tok
            else:
                yield t,v,b,e,l
                yield tt,vv,bb,ee,ll
        else:
            yield t,v,b,e,l

def _expand_quoted_code_expr(tokenstream):
    '''Expand ${...} constructs in a tokenstream into 
    a call to expand_code_template'''
    tpl_text = tokenize.untokenize(tokenstream)
    new_text = '__expand_code_template(\n%r\n, globals(), locals())' % tpl_text
    for tok in tokenize.generate_tokens(StringIO(new_text).readline):
        yield tok

            
def _read_suite(tokenstream, keep_header=False, colon_already_read=False):
    '''Read an indented suite of statements (or an inline suite) from a
    tokenstream

    :arguments:
       tokenstream
         the token stream
       keep_header
         whether to emit the header (text before the colon)
       colon_already_read
         if false, the suite will begin after the next colon
    '''
    # read to the colon
    t=v=None
    if not colon_already_read:
        while (t,v) != (token.OP, ':'):
            t,v,b,e,l = tokenstream.next()
            if keep_header: yield t,v,b,e,l
    t,v,b,e,l = tokenstream.next()
    if keep_header: yield t,v,b,e,l
    if t == token.NEWLINE:
        # Case 1: the next token is a newline -- so read an indented block
        for tok in _read_block(tokenstream, keep_header):
            yield tok
    else:
        # Case 2: the next token is not a newline -- so read till the newline
        while t != token.NEWLINE:
            t,v,b,e,l = tokenstream.next()
            yield t,v,b,e,l

def _read_block(tokenstream, keep_header=False):
    '''Read an indented block'''
    # Read to the indent
    t=v=None
    while t != token.INDENT:
        t,v,b,e,l = tokenstream.next()
        if keep_header:
            yield t,v,b,e,l
    # Read to the unindent
    n_indent = 1
    while n_indent > 0:
        t,v,b,e,l = tokenstream.next()
        if t == token.INDENT:
            n_indent += 1
        elif t == token.DEDENT:
            n_indent -= 1
        if n_indent != 0:
            yield t,v,b,e,l

def _read_args(tokenstream):
    '''Read an argument list: a list of expressions separated by commas and
    terminated with a close-paren'''
    while True:
        toks = []
        for t,v,b,e,l in _read_nested(
            tokenstream, ',', ')'):
            toks.append((t,v,b,e,l))
        yield Code(*toks[:-1])
        if v == ')': break

def _read_nested(tokenstream, *closing_ops):
    '''Read a possibly nested expression.  The closing_ops are the operators
    which can close the expression.'''
    closing_ops = set(closing_ops)
    while True:
        t,v,b,e,l = tokenstream.next()
        yield t,v,b,e,l
        if t==token.OP:
            if v in closing_ops:
                break
            elif v in NESTING_OPS:
                for tok in _read_nested(tokenstream, NESTING_OPS[v]):
                    yield tok

def pprint_toks(toks):
    '''Print tokens with their symbolic names & values'''
    print pformat_toks(toks)

def pformat_toks(toks):
    '''Format tokens with their symbolic names & values'''
    l = []
    for t in toks:
        l.append('%s(%r)' % (token.tok_name[t[0]], t[1]))
    return '\n'.join(l)

def expand_code_template(template_text, gbl, lcl):
    '''Create a Jinja2 template from template_text and expand it
    in a namespace created from the gbl and lcl dicts.  Any code objects in gbl
    and lcl are converted to strings before expansion.
    '''
    # Expand the tokens to their textual representation
    def _():
        for k,v in dict(gbl, **lcl).iteritems():
            if isinstance(v, Code):
                v = str(v)
            yield k,v
    ns = dict(_())
    ns.update(__builtins__)
    tpl = Template(template_text,
                   variable_start_string='$',
                   variable_end_string='$')
    text = tpl.render(ns)
    tokens = list(tokenize.generate_tokens(StringIO(text.encode('utf-8')).readline))
    return Code(*tokens)

