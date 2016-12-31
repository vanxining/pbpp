import unittest

from .... import Converters
from .. import conv


def set_ref_field(m):
    m.tmp_f().a = m.A.get()


def set_non_copy_assignable_field(m):
    h = m.H()
    h.g = m.G()


class Test(unittest.TestCase):
    def runTest(self):
        Converters.push(conv.WstringConv())

        from .. import full_process
        m = full_process.run2(__file__)

        Converters.pop()

        for cls in range(ord('A'), ord('I') + 1):
            self.assertTrue(hasattr(m, chr(cls)))

        self.assertEqual(m.tmp_f().foo(), 5678)
        self.assertEqual(m.tmp_f().a.count, 999)
        self.assertRaises(AttributeError, set_ref_field, m)

        fobj = m.tmp_f()
        self.assertEqual(fobj.field.num, 0)

        fobj.field.num += 100
        self.assertEqual(fobj.field.num, 100)

        field1 = fobj.field
        self.assertEqual(field1.num, 100)
        self.assertNotEqual(fobj.field, field1)
        self.assertNotEqual(id(fobj.field), id(field1))

        field2 = m.Field()
        field2.num = 1990
        fobj.field = field2
        self.assertEqual(fobj.field.num, 1990)
        self.assertNotEqual(fobj.field, field2)
        self.assertNotEqual(id(fobj.field), id(field2))

        self.assertEqual(m.H().g.field.num, 0)
        self.assertRaises(AttributeError, set_non_copy_assignable_field, m)

        i1 = m.I()
        self.assertEqual(i1.num, 0)
        self.assertEqual(i1.str, u"Hello, world!")

        i1.num = 256
        i1.str = u"PyBridge++"
        self.assertEqual(i1.num, 256)
        self.assertEqual(i1.str, u"PyBridge++")

        i2 = m.I(i1)
        self.assertEqual(i2.num, i1.num)
        self.assertEqual(i2.str, i1.str)
