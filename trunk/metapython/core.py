'''Metapython syntax extensions
'''
from __future__ import with_statement
import os
import new
import sys
import token
from cStringIO import StringIO

from metapython import parse

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
        try:
            first_token = iter(inp3).next()
            if first_token.match(token.STRING):
                doc = first_token.value
            else:
                doc = None
        except StopIteration, si:
            doc = None
        return doc, inp3.as_python()

