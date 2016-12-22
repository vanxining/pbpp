import unittest


# Test object reference argument with default value.
class Test(unittest.TestCase):
    def runTest(self):
        from .. import full_process
        m = full_process.run2(__file__)

        self.assertEqual(m.foo(), 124)
        self.assertEqual(m.foo(m.dummy(999)), 1000)
