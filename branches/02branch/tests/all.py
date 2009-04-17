import os
import unittest

import metapython
from metapython import parse
from metapython.parse import Builder

from base import MetaPythonTest

class TestCodeQuoting(MetaPythonTest):

    def testQuoteSimple(self):
        inp = parse.parse_string('print "hi"')
        inp1 = inp.quote('foo')
        ns = dict(_mpy = Builder())
        inp1.exec_(ns, ns)
        inp2 = ns['foo']
        golden1 = parse.parse_string('''_mpy.push()
_mpy.append('print "hi"', globals(), locals())
foo = _mpy.pop()''')
        self.assertEqualCode(inp1, golden1)
        self.assertEqualCode(inp, inp2)

    def testQuoteSuite(self):
        inp = parse.parse_string('''for x in range(10):
    print x''')
        inp1 = inp.quote('foo')
        ns = dict(_mpy = Builder())
        inp1.exec_(ns, ns)
        inp2 = ns['foo']
        self.assertEqualCode(inp, inp2)

    def testQuoteSimpleMacro(self):
        inp = parse.parse_string('''$for x in range(3):
    print $x''')
        inp1 = inp.quote('foo')
        ns = dict(_mpy = Builder())
        inp1.exec_(ns, ns)
        inp2 = ns['foo']
        self.assertEqualCode(inp2, '''print 0
print 1
print 2''')

    def testSimple(self):
        inp = parse.parse_string('''defcode x:
    $for i in range(10):
        print "hi", $i''')
        golden1 = parse.parse_string('''_mpy.push()
for i in range(10):
    _mpy.append('print "hi",$i ', globals(), locals())
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
        ns = dict(_mpy=Builder())
        inp_expanded.exec_(ns, ns)
        self.assertEqualCode(ns['x'], golden2)

    def testQuoteBlock(self):
        inp = parse.parse_string('''defcode x:
    for i in range(10):
        print i''')
        inp1 = inp.expand_defcode_blocks()
        ns = dict(_mpy=Builder())
        inp1.exec_(ns, ns)
        self.assertEqualCode(ns['x'], '''for i in range(10):
    print i''')

    def testShortQuote(self):
        inp = parse.parse_string('''foo(?pass)''')
        inp1 = inp.expand_defcode_blocks()
        self.assertEqualCode(inp1, "foo(_mpy.q('pass '))")

class TestMacro(MetaPythonTest):

    def testSimple(self):
        inp = parse.parse_string('''$: j = 50
$for i in range(10):
    print $i, $j''')
        inp1 = inp.expand()
        golden = '\n'.join('print %d,50' % i for i in range(10))
        self.assertEqualCode(inp1, golden)

    def testDefcode(self):
        ns = dict(_mpy=Builder())
        inp = parse.parse_string('''j=50
defcode result:
    $for i in range(10):
        print $i, $j''')
        inp1 = inp.expand_defcode_blocks()
        inp1.exec_(ns, ns)
        self.assertEqualCode(
            ns['result'],
            '\n'.join('print %d, 50' % i for i in range(10)))

    def testFile(self):
        inp = parse.parse_file(
            os.path.join(os.path.dirname(__file__),
                         'namedtuple.mpy'))
        inp1 = inp.expand_defcode_blocks()
        _mpy = Builder()
        ns = dict(_mpy=_mpy)
        inp1.exec_(ns, ns)
        inp2 = parse.parse_string('$namedtuple(?Point, ?x, ?y)')
        inp3 = inp2.expand_defcode_blocks()
        inp4 = inp3.quote()
        inp4.namespace = ns
        _mpy.push()
        inp4.exec_(ns, ns)
        expanded = _mpy.pop()
        expanded.exec_(ns, ns)
        self.assertEqual(str(ns['Point'](1,2)),
                         'Point (x =1, y =2)')

class TestImport(MetaPythonTest):

    def setUp(self):
        metapython.install_import_hook()

    def testNamedTuple(self):
        import test1
        p = test1.Point(1,2)
        self.assertEqual(str(p), 'Point (x =1, y =2)')

    def testNested(self):
        import test2
        # print test2.__expanded__

if __name__ == '__main__':
    unittest.main()
