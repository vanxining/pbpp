import unittest

from .... import Converters
from .... import Types


# Test the conversion between C++ std::map and Python dict
class Test(unittest.TestCase):
    def runTest(self):
        Converters.add(Converters.StrConv())

        # Cannot write as ("char", "const", "*"): blame Clang
        K = Types.Type(("const", "char", "*",), 0, "PointerType")
        V = Types.Type(("int",), 0, "FundamentalType")
        Converters.add(Converters.DictConv(K, V))

        from .. import full_process
        m = full_process.run2(__file__)

        Converters.pop()
        Converters.pop()

        d = {
            "price": 123,
            "count": 5,
        }
        m.foo(d)

        self.assertEqual(d["price"], 456)
        self.assertEqual(len(d), 3)
        self.assertEqual(d["index"], 999)
