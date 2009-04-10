import os
import token
import unittest

from metapython import parse, builder

class MetaPythonHelper(object):
    Block = parse.Block
    Stmt = parse.Stmt
    Suite = parse.Suite
    Token = parse.Token
    tokens_from_string = staticmethod(parse.tokens_from_string)
    token = token

    def __init__(self):
        self.stack = [ ]

    def push(self, namespace):
        self.stack.append(parse.Block(namespace=namespace))

    def pop(self):
        return self.stack.pop()

    @property
    def top(self):
        return self.stack[-1]

class MetaPythonTest(unittest.TestCase):

    def assertEqualCode(self, c0, c1):
        if hasattr(c0, 'as_python'):
            c0 = c0.as_python()
        if hasattr(c1, 'as_python'):
            c1 = c1.as_python()
        if not c0.endswith('\n'): c0+= '\n'
        if not c1.endswith('\n'): c1+= '\n'
        l0 = list(parse.tokens_from_string(c0))
        l1 = list(parse.tokens_from_string(c1))
#         if l0 != l1:
#             for t0, t1 in zip(l0, l1):
#                 print '%10s(%20r)  %10s(%20r)' % (
#                     t0.tok_name, t0.value, t1.tok_name, t1.value)
        error_message = '''Code blocks are not equal:
%s
===
%s''' % (c0, c1)
        self.assertEqual(l0, l1, error_message)
     
class TestCodeQuoting(MetaPythonTest):

    def testQuoteSimple(self):
        inp = parse.parse_string('print "hi"')
        inp1 = inp.quote('foo')
        inp1.namespace = dict(_mpy = builder.Builder())
        inp1.exec_()
        inp2 = inp1.namespace['foo']
        golden1 = parse.parse_string('''_mpy.push()
_mpy.append('print "hi"')
foo = _mpy.pop()''')
        self.assertEqualCode(inp1, golden1)
        self.assertEqualCode(inp, inp2)

    def testQuoteSuite(self):
        inp = parse.parse_string('''for x in range(10):
    print x''')
        inp1 = inp.quote('foo')
        inp1.namespace = dict(_mpy = builder.Builder())
        inp1.exec_()
        inp2 = inp1.namespace['foo']
        self.assertEqualCode(inp, inp2)

    def testQuoteSimpleMacro(self):
        inp = parse.parse_string('''?for x in range(3):
    print $x''')
        inp.namespace = dict(_mpy = builder.Builder())
        inp1 = inp.quote('foo')
        inp1.namespace = dict(_mpy = builder.Builder())
        inp1.exec_()
        inp2 = inp1.namespace['foo']
        print inp.as_python()
        print '==='
        print inp1.as_python()
        print '==='
        print inp2.as_python()
        print '==='
        

    def testSimple(self):
        inp = parse.parse_string('''defcode x:
    $for i in range(10):
        print "hi", $i''')
        golden1 = parse.parse_string('''_mpy.push()
for i in range(10):
    _mpy.append('print "hi",$i ')
x = _mpy.pop()
''')
        golden2 = parse.parse_string('''print "hi", 0
print "hi", 1
print "hi", 2
print "hi", 3
print "hi", 4
print "hi", 5
print "hi", 6
print "hi", 7
print "hi", 8
print "hi", 9''')
        inp_expanded = inp.expand_defcode_blocks()
        self.assertEqualCode(inp_expanded, golden1)
        inp_expanded.namespace = ns = dict(_mpy=MetaPythonHelper())
        inp_expanded.exec_()
        self.assertEqualCode(ns['x'], golden2)

    def testQuoteBlock(self):
        inp = parse.parse_string('''defcode x:
    for i in range(10):
        print i''')
        print inp.as_python()
        inp1 = inp.expand_defcode_blocks()
        print inp1.as_python()
        inp1.namespace = ns = dict(_mpy=MetaPythonHelper())
        inp1.exec_()
        print ns['x'].as_python()


class TestMacro(MetaPythonTest):

    def testSimple(self):
        inp = parse.parse_string('''$: j = 50
$for i in range(10):
    print $i, $j''')
        inp1 = inp.expand()
        golden = '\n'.join('print %d,50' % i for i in range(10))
        self.assertEqualCode(inp1, golden)

    def testDefcode(self):
        ns = dict(_mpy=MetaPythonHelper())
        inp = parse.parse_string('''j=50
defcode result:
    for i in range(10):
        print $i $j''', namespace=ns)
        import pdb; pdb.set_trace()
        inp1 = inp.expand_defcode_blocks()
        print inp.as_python()
        print inp1.as_python()
        inp1.exec_()
        print inp1.namespace.keys()
        print inp1.namespace['result'].as_python()


    def testFile(self):
        inp = parse.parse_file(
            os.path.join(os.path.dirname(__file__),
                         'namedtuple.mpy'))
        print inp.as_python()
        inp1 = inp.expand_defcode_blocks()
        print inp1.as_python()
        inp2 = inp1.quote('_mpy')
        block = parse.parse_string('_mpy.push(locals())')
        block.add(inp2)
        _mpy = MetaPythonHelper()
        block.namespace = ns = dict(_mpy=_mpy)
        print block.as_python()
        block.exec_()
        mod_text = _mpy.result.as_python()
        print mod_text
        exec mod_text in ns
        namedtuple = ns['namedtuple']
        text = namedtuple(
            parse.parse_string('foo'),
            parse.parse_string('a'))
        print text
        
if __name__ == '__main__':
    unittest.main()
