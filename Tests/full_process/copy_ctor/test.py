import unittest
from .... import Converters


def set_ref_field(m):
    m.tmp_f().a = m.A.get()


def set_non_copy_assignable_field(m):
    h = m.H()
    h.g = m.G()


class WstringConv(Converters.Converter):
    def match(self, cpp_type):
        if cpp_type.intrinsic_type() == "wstring":
            if not cpp_type.is_trivial():
                if cpp_type.is_const() or not cpp_type.has_decorators():
                    return True

        return False

    def specifier(self, cpp_type):
        return "u"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        init_expr = "nullptr"
        if defv is not None:
            init_expr = "(const wchar_t *) " + defv

        return "const wchar_t *%s = %s;" % (var_name, init_expr)

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        return "&" + arg_name

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        return ""

    def args_parsing_require_error_handling(self, cpp_type):
        return False

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyUnicode_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        var = "(const wchar_t *) PyUnicode_AsUnicode(%s)" % py_var_name
        return cpp_type.declare_var(var_name, var)

    def value_building_interim_var(self, arg_name):
        return arg_name + ".c_str()"

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        common_part = "PyUnicode_FromWideChar({1}.c_str(), {1}.length())"
        boilerplate = "pbpp::PyObjectPtr {{0}}({});" if raii else "PyObject *{{0}} = {};"

        return boilerplate.format(common_part).format(py_var_name, var_name)


class Test(unittest.TestCase):
    def runTest(self):
        Converters.push(WstringConv())

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
