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
        inp = parse.parse_string('''defcode x():
    $for i in range(10):
        print "hi", $i''')
        golden1 = parse.parse_string('''_mpy.push()
for i in range(10):
    _mpy.append('print "hi",$i ', globals(), locals())
x = _mpy.pop()
x = x.sanitize(globals(), locals(),)
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
        inp = parse.parse_string('''defcode x():
    for i in range(10):
        print i''')
        inp1 = inp.expand_defcode_blocks()
        ns = dict(_mpy=Builder())
        inp1.exec_(ns, ns)
        self.assertEqualCode(ns['x'], '''for _mpy_1 in range(10):
    print _mpy_1''')

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
defcode result():
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
        self.assert_(test2.__expanded__)

class TestHygene(MetaPythonTest):

    def testReplaceName(self):
        inp = parse.parse_string('j=50')
        inp1 = inp.replace_names(j='foo')
        self.assertEqualCode(inp1, 'foo=50')

    def testSanitize(self):
        inp = parse.parse_string('j=50')
        inp1 = inp.sanitize({}, {})
        self.assert_('j' not in str(inp1))
        
    def testSanitizePartial(self):
        inp = parse.parse_string('j=i')
        ns = dict(_mpy = Builder())
        inp1 = inp.sanitize(ns, ns, '_mpy.q("i")')
        self.assert_('j' not in str(inp1))
        self.assert_('i' in str(inp1))

    def testAutoSanitize(self):
        inp = parse.parse_string('''
defcode result(?i):
    i = 'foo'
    j = 'bar'
''')
        inp1 = inp.expand_defcode_blocks()
        ns = dict(_mpy=Builder())
        inp1.exec_(ns, ns)
        result = str(ns['result'])
        self.assert_('i' in result)
        self.assert_('j' not in result)
        inp = parse.parse_string('''
defcode result():
    i = 'foo'
    j = 'bar'
''')
        inp1 = inp.expand_defcode_blocks()
        ns = dict(_mpy=Builder())
        inp1.exec_(ns, ns)
        result = str(ns['result'])
        self.assert_('i' not in result)
        self.assert_('j' not in result)

    def testSetMacro(self):
        inp = parse.parse_string('''
def set_(var, value):
    defcode result(var):
        $var = $value
    return result
''')
        ns = dict(_mpy=Builder())
        inp1 = inp.expand_defcode_blocks()
        inp1.exec_(ns, ns)
        inp2 = parse.parse_string('$set_(?A, 5)')
        inp3 = inp2.expand(ns, ns)
        self.assertEqualCode(inp3, 'A=5')

    def testSetI(self):
        inp = parse.parse_string('''
def seti(value):
    defcode result(?i):
        i = $value
    return result
''')
        ns = dict(_mpy=Builder())
        inp1 = inp.expand_defcode_blocks()
        inp1.exec_(ns, ns)
        inp2 = parse.parse_string('$seti(5)')
        inp3 = inp2.expand(ns, ns)
        self.assertEqualCode(inp3, 'i=5')
        

if __name__ == '__main__':
    unittest.main()
