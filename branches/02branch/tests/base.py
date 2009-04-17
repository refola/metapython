import unittest

from metapython import parse


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
        error_message = '''Code blocks are not equal:
%s
===
%s''' % (c0, c1)
        self.assertEqual(l0, l1, error_message)
     
