import unittest


class Test(unittest.TestCase):
    def runTest(self):
        from .. import full_process
        m = full_process.run2(__file__)

        self.assertEqual(m.foo(1, 2, 3, 4.5, 10.5), 21)
