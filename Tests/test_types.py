import os
import unittest

from .. import Converters
from .. import HeaderJar
from .. import Session
from .. import Types


def current_directory():
    return os.path.dirname(os.path.realpath(__file__))


class TestTypes(unittest.TestCase):
    def setUp(self):
        header_jar = HeaderJar.HeaderJar()
        Session.begin(header_jar)

        Converters.add(Converters.WcsConv())

        integer = Types.Type(("int",), 99, "FundamentalType")
        Converters.add(Converters.ListConv(integer))
        Converters.add(Converters.DictConv(integer, integer))

    def tearDown(self):
        Session.end()

    def test_get_type_by_id(self):
        from xml.etree.ElementTree import parse

        root = parse(current_directory() + "/raw/Y.xml").getroot()
        if root is not None:
            tp = Types.get_type_by_id("_6576c", root)
            self.assertEqual(tp.decl(), "Y *const")
            self.assertEqual(tp.declare_var("const_ptr", "nullptr", strip_last_const=False),
                             "Y *const const_ptr = nullptr;")
            self.assertEqual(tp.declare_var("const_ptr", "nullptr"),
                             "Y *const_ptr = nullptr;")

    def test_declaring_to_assigning(self):
        from ..Types import Type, declaring_to_assigning

        tp = Types.Type(("int",), 11, "FundamentalType")

        code = "int x = 123;"
        self.assertEqual(declaring_to_assigning(tp, "x", code), "x = 123;")

        code = "int x(123);"
        self.assertEqual(declaring_to_assigning(tp, "x", code), "x = (123);")

        code = "int x;\nx = 12345;"
        self.assertEqual(declaring_to_assigning(tp, "x", code), "x = 12345;")

        tp = Types.Type(("PyObject", "*",), 11, "PointerType")
        borrow_from_ptr = '''PyObject *py_item_raw;
if (item) {
    PyObject *Borrow__Point(const wxPoint &from);
    py_item_raw = Borrow__Point(*item);
} else {
    Py_INCREF(Py_None);
    py_item_raw = Py_None;
}
PyObject *py_item = py_item_raw;'''
        self.assertEqual(declaring_to_assigning(tp, "py_item", borrow_from_ptr),
                         '''PyObject *py_item_raw;
if (item) {
    PyObject *Borrow__Point(const wxPoint &from);
    py_item_raw = Borrow__Point(*item);
} else {
    Py_INCREF(Py_None);
    py_item_raw = Py_None;
}
py_item = py_item_raw;''')

        tp = Types.Type(("const", "char", "*",), 0, "PointerType")
        code = 'const char *key = nullptr;\nkey = PyString_AsString("KEY");'
        self.assertEqual(declaring_to_assigning(tp, "key", code),
                         'key = nullptr;\nkey = PyString_AsString("KEY");')

    def test_types(self):
        pass
