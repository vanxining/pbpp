import unittest

from .... import Converters
from .... import Types
from .. import conv


class DictConv(Converters.DictConv):
    def __init__(self, *args, **kwargs):
        Converters.DictConv.__init__(self, *args, **kwargs)

    def match(self, cpp_type):
        return cpp_type.decl().startswith("std::map<std::basic_string<wchar_t")


# Test the conversion between C++ std::map and Python dict
class Test(unittest.TestCase):
    def runTest(self):
        Converters.push(conv.WstringConv())

        # `const char *` is not comparable!
        K = Types.Type(("wstring",), 0, "Class")
        V = Types.Type(("int",), 0, "FundamentalType")
        Converters.add(DictConv(K, V))

        from .. import full_process
        m = full_process.run2(__file__)

        Converters.pop()
        Converters.pop()

        d = {
            u"price": 123,
            u"count": 5,
        }
        m.foo(d)

        self.assertEqual(d[u"price"], 456)
        self.assertEqual(len(d), 3)
        self.assertEqual(d[u"index"], 999)
