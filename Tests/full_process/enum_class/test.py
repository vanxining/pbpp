import unittest


class TestEnumClass(unittest.TestCase):
    def runTest(self):
        from .. import full_process
        m = full_process.run2(__file__)

        self.assertEqual(m.Color.RED, 0)
        self.assertEqual(m.Color.GREEN, 1)
        self.assertEqual(m.Color.BLUE, 255)
