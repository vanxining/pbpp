import os
import unittest

from .. import CodeBlock
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
        block = CodeBlock.CodeBlock()

        tp = Types.Type(("long int",), 11, "FundamentalType")
        block.write_code(tp.get_build_value_idecl("x"))
        block.write_code(tp.get_extractor_code("xx", "py_x", "return nullptr;"))
        self.assertEqual(block.flush(), '''PyObject *py_x = PyLong_FromLong(x);
if (!pbpp::Types::IsNumber((PyObject *) py_x)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `long int` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
long int xx = pbpp::Types::ToLong(py_x);''')

        tp = Types.Type(("double", "const"), 12, "FundamentalType")
        block.write_code(tp.get_build_value_idecl("d"))
        block.write_code(tp.get_extractor_code("dd", "py_d", "return nullptr;"))
        self.assertEqual(block.flush(), '''PyObject *py_d = PyFloat_FromDouble(d);
if (!pbpp::Types::IsNumber((PyObject *) py_d)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `double const` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
double const dd = pbpp::Types::ToDouble(py_d);''')

        tp = Types.Type(("double", "*",), 13, "FundamentalType")
        block.write_code(tp.get_build_value_idecl("dp"))
        block.write_code(tp.get_extractor_code("dp2", "py_dp", "return nullptr;"))
        block.write_code(tp.declare_var("dp3", "nullptr"))
        self.assertEqual(block.flush(), '''PyObject *py_dp = (dp) ? PyCapsule_New((void *) dp, "double *", nullptr) : Py_None;
double *dp2 = nullptr;
if (py_dp != Py_None) {
    if (!PyCapsule_IsValid(py_dp, "double *")) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `double *` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    dp2 = (double *) PyCapsule_GetPointer(py_dp, "double *");
}
double *dp3 = nullptr;''')

        tp = Types.Type(("float", "*", "*", "*", "const",), 14, "FundamentalType")
        block.write_code(tp.get_build_value_idecl("fp"))
        block.write_code(tp.get_extractor_code("fp2", "py_fp", "return nullptr;"))
        block.write_code(tp.declare_var("fp3", "nullptr"))
        self.assertEqual(block.flush(), '''PyObject *py_fp = (fp) ? PyCapsule_New((void *) fp, "float ***", nullptr) : Py_None;
float ***fp2 = nullptr;
if (py_fp != Py_None) {
    if (!PyCapsule_IsValid(py_fp, "float ***")) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `float ***const` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    fp2 = (float ***const) PyCapsule_GetPointer(py_fp, "float ***");
}
float ***fp3 = nullptr;''')

        tp = Types.Type(("bool",), 15, "FundamentalType")
        block.write_code(tp.get_build_value_idecl("flag"))
        block.write_code(tp.get_extractor_code("flag2", "py_flag", "return nullptr;"))
        block.write_code(tp.declare_var("flag3", "false"))
        self.assertEqual(block.flush(), '''PyObject *py_flag = PyBool_FromLong(flag);
if (!PyBool_Check((PyObject *) py_flag)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `bool` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
bool flag2 = (PyObject_IsTrue(py_flag) == 1);
bool flag3 = false;''')

        tp = Types.Type(("wchar_t", "const", "*"), 222, "PointerType")
        block.write_code(tp.get_build_value_idecl("s"))
        block.write_code(tp.get_extractor_code("ss", "py_s", "return nullptr;"))
        self.assertEqual(block.flush(), '''PyObject *py_s = PyUnicode_FromWideChar(s, wcslen(s));
wchar_t const *ss = nullptr;
if (py_s != Py_None) {
    if (!PyUnicode_Check((PyObject *) py_s)) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `wchar_t const *` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    ss = (const wchar_t *) PyUnicode_AsUnicode(py_s);
}''')


        from namer import TestNamer
        namer = TestNamer()

        tp = Types.Type(("wxSize", "const",), 16, "Class")
        block.write_code(tp.get_build_value_idecl("sz", namer=namer))
        block.write_code(tp.get_extractor_code("sz2", "py_sz", "return nullptr;", namer=namer))
        self.assertEqual(block.flush(), '''PyObject *Copy__wxSize(const wxSize &from, pbpp_flag_t flags);
PyObject *py_sz = Copy__wxSize(sz, pbpp::LifeTime::PYTHON);
extern PyTypeObject wxSize__Type;
if (!PyObject_TypeCheck(py_sz, &wxSize__Type)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `wxSize const` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
wxSize sz2(**((wxSize **) (((unsigned long)(PyObject *) py_sz) + sizeof(PyObject))));''')

        tp = Types.Type(("wxSize", "const", "*",), 17, "Class")
        block.write_code(tp.get_build_value_idecl("sz2", namer=namer))
        block.write_code(tp.get_extractor_code("sz3", "py_sz2", "return nullptr;", namer=namer))
        self.assertEqual(block.flush(), '''PyObject *py_sz2_raw;
if (sz2) {
    PyObject *Borrow__wxSize(const wxSize &from);
    py_sz2_raw = Borrow__wxSize(*sz2);
} else {
    Py_INCREF(Py_None);
    py_sz2_raw = Py_None;
}
PyObject *py_sz2 = py_sz2_raw;
wxSize const *sz3 = nullptr;
if (py_sz2 != Py_None) {
    extern PyTypeObject wxSize__Type;
    if (!PyObject_TypeCheck(py_sz2, &wxSize__Type)) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `wxSize const *` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    sz3 = *((wxSize **) (((unsigned long)(PyObject *) py_sz2) + sizeof(PyObject)));
}''')

        tp = Types.Type(("wxSize", "const", "&",), 18, "Class")
        block.write_code(tp.get_build_value_idecl("sz3", namer=namer))
        block.write_code(tp.get_extractor_code("sz4", "py_sz3", "return nullptr;", namer=namer))
        self.assertEqual(block.flush(), '''PyObject *Borrow__wxSize(const wxSize &from);
PyObject *py_sz3 = Borrow__wxSize(sz3);
extern PyTypeObject wxSize__Type;
if (!PyObject_TypeCheck(py_sz3, &wxSize__Type)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `wxSize const &` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
wxSize const &sz4 = **((wxSize **) (((unsigned long)(PyObject *) py_sz3) + sizeof(PyObject)));''')

        tp = Types.Type(("std::vector<int>", "const", "&",), 19, "Class")
        block.write_code(tp.get_build_value_idecl("v1", namer=namer))
        block.write_code(tp.get_extractor_code("v2", "py_v1", "return nullptr;", namer))
        self.assertEqual(block.flush(), '''PyObject *py_v1 = PyList_New(v1.size());
for (std::vector<int>::size_type i = 0, cnt = v1.size(); i < cnt; i++) {
    PyObject *py_item = PyInt_FromSsize_t(v1[i]);
    PyList_SetItem(py_v1, i, py_item);
}
if (!PyList_Check((PyObject *) py_v1)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `std::vector<int> const &` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
std::vector<int> v2;
Py_ssize_t __len = PySequence_Length(py_v1);
for (Py_ssize_t i = 0; i < __len; i++) {
    PyObject *py_item = PySequence_ITEM(py_v1, i);
    if (!pbpp::Types::IsNumber((PyObject *) py_item)) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `int` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    int item = pbpp::Types::ToInt(py_item);
    v2.push_back(item);
}''')

        header_jar = Session.header_jar()
        self.assertEqual(header_jar.concat_sorted(), '#include "_List.hxx"')
        header_jar.clear()

        tp = Types.Type(("std::map<int,int>", "const", "&",), 20, "Class")
        block.write_code(tp.get_build_value_idecl("m", namer=namer))
        block.write_code(tp.get_extractor_code("m2", "py_m", "return nullptr;", namer))
        self.assertEqual(block.flush(), '''PyObject *py_m = PyDict_New();
for (auto &kv : m) {
    PyObject *py_dict_key = PyInt_FromSsize_t(kv.first);
    PyObject *py_dict_value = PyInt_FromSsize_t(kv.second);
    PyDict_SetItem(py_m, py_dict_key, py_dict_value);
    Py_DECREF(py_dict_key);
    Py_DECREF(py_dict_value);
}
if (!PyDict_Check((PyObject *) py_m)) {
    PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `std::map<int,int> const &` is required.", __FILE__, __LINE__, __FUNCTION__);
    return nullptr;
}
std::map<int,int> m2;
PyObject *py_dict_key, *py_dict_value;
Py_ssize_t __pos = 0;
while (PyDict_Next(py_m, &__pos, &py_dict_key, &py_dict_value)) {
    if (!pbpp::Types::IsNumber((PyObject *) py_dict_key)) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `int` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    int key = pbpp::Types::ToInt(py_dict_key);
    if (!pbpp::Types::IsNumber((PyObject *) py_dict_value)) {
        PyErr_Format(PyExc_TypeError, "[%s:%d<%s>] Object of type `int` is required.", __FILE__, __LINE__, __FUNCTION__);
        return nullptr;
    }
    int value = pbpp::Types::ToInt(py_dict_value);
    m2[key] = value;
}''')
        self.assertEqual(header_jar.concat_sorted(), '#include "_Dict.hxx"')
        header_jar.clear()


if __name__ == "__main__":
    unittest.main()
