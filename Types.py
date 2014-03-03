import Code.Snippets
import Util

from collections import deque

#---------------------------------------------------------------------------#

BUILT_IN = 1
REFERENCE = 2
POINTER = 3
CLASS = 4


class Type:
    def __init__(self, decl_list, tag):
        assert isinstance(decl_list, (list, tuple, deque,))
        assert len(decl_list) > 0
        assert isinstance(tag, str)

        self.decl_list = decl_list
        self.decl_list_no_const = [d for d in decl_list if d != "const"]
        self.tag = tag

    def decl(self):
        return self._fmt(' '.join(self.decl_list))

    def decl_no_const(self):
        return self._fmt(' '.join(self.decl_list_no_const))

    @staticmethod
    def _fmt(decl):
        return decl.replace("* ", "*")

    def intrinsic_type(self):
        return self.decl_list[0]

    def category(self):
        if self.is_built_in():
            return BUILT_IN
        elif self.is_ptr():
            return POINTER
        elif self.is_ref():
            return REFERENCE
        else:
            return CLASS

    def is_bool(self):
        return self.decl_no_const() == "bool"

    def is_enum(self):
        return self.tag == "Enumeration"

    def is_ptr_or_ref(self):
        return self.is_ref() or self.is_ptr()

    def is_ref(self):
        return self.decl_list_no_const[-1] == '&'

    def is_ptr(self):
        return self.decl_list_no_const[-1] == '*'

    def is_built_in(self):
        return self.is_enum() or ((
            len(self.decl_list_no_const) == 1 and
            self.decl_list_no_const[0] in _built_in
        ))

    def is_trivial(self):
        if self.is_built_in():
            return True

        if self.is_ptr_or_ref():
            secondary_decl = self.decl_list_no_const[-2]
            if secondary_decl in _built_in or secondary_decl in "&*":
                return True

        return False

    def ref_to_ptr(self):
        assert self.is_ptr_or_ref()

        ret = [oper for oper in self.decl_list]
        for index, oper in enumerate(ret):
            if oper == '&':
                ret[index] = '*'
                break

        return Type(ret, self.tag)

    def get_specifier(self):
        if self.is_built_in():
            if self.is_enum():
                return 'i'
            else:
                return _built_in[self.decl_no_const()]["specifier"]
        else:
            return "O!"

    def join_type_and_name(self, name):
        if self.decl_list[-1] in "&*":
            return self.decl() + name
        else:
            return "%s %s" % (self.decl(), name)

    def declate_var(self, name, init=None):
        decl = self.join_type_and_name(name)

        if init is not None:
            if self.category() == CLASS:
                return decl + "(%s);" % init
            else:
                return decl + " = %s;" % init
        else:
            return decl + ";"

    def get_build_value_idecl(self, var_name, namer=None):
        if self.is_built_in():
            ret = "PyObject *py_%s = " % var_name
            if self.is_enum():
                builder = _built_in["int"]["builder"]
            else:
                builder = _built_in[self.decl_no_const()]["builder"]

            return ret + builder + "(%s);" % var_name
        elif self.is_ptr_or_ref():
            if self.is_trivial():
                addr = "&(%s)"
                if self.is_ptr():
                    addr = addr[1:]

                return Code.Snippets.PyCapsule_New % (
                    var_name, addr % var_name, self.decl_no_const()
                )
            else:
                assert namer

                if self.is_ref():
                    addr = '&' + var_name
                    ref = var_name
                else:
                    addr = var_name
                    ref = '*' + var_name

                return Code.Snippets.wrap_nontrivial_borrowed_ref % {
                    "VAR_NAME": var_name,
                    "REF": ref, "ADDR": addr,
                    "WRAPT": namer.wrapper_class(self.intrinsic_type()),
                    "PYOBJ_STRUCT": namer.pyobj(self.intrinsic_type()),
                    "PYTYPE": namer.pytype(self.intrinsic_type()),
                }
        else:
            assert namer

            return Code.Snippets.return_by_value % {
                "VAR_NAME": var_name,
                "CLASS": self.intrinsic_type(),
                "CLS_EMBBEDED": namer.to_python(self.intrinsic_type()),
            }


class Registry:

    _registry = {}
    _black_list = set()

    def __init__(self):
        pass

    @staticmethod
    def get(item, default=None):
        return Registry._registry.get(item, default)

    @staticmethod
    def load_from_file(path):
        raise NotImplementedError

    @staticmethod
    def save_to_file(path):
        raise NotImplementedError

    @staticmethod
    def add(tp):
        assert isinstance(tp, Type)

        if tp.decl() not in Registry._black_list:
            Registry._registry[tp.decl()] = tp

    @staticmethod
    def add_to_black_list(lst):
        assert isinstance(lst, (list, tuple))

        for cls in lst:
            Registry._black_list.add(cls)


def _get_node_by_id(node_id, root):
    return root.find(".//*[@id='%s']" % node_id)


def _is_function_pointer(node, root):
    while "type" in node.attrib:
        node = _get_node_by_id(node.attrib["type"], root)

    return node.tag in ("FunctionType", "MethodType")


def get_type_from_id(type_node_id, root):
    assert isinstance(type_node_id, str)
    assert root is not None

    decl = deque()

    while True:
        node = _get_node_by_id(type_node_id, root)

        if _is_function_pointer(node, root):
            raise RuntimeError("Function pointer / pointer to member "
                               "is not supported yet.")

        if "name" not in node.attrib:
            if node.tag == "ReferenceType":
                decl.appendleft('&')
            elif node.tag == "PointerType":
                decl.appendleft('*')

            type_node_id = node.attrib["type"]
            if type_node_id.endswith('c'):
                type_node_id = type_node_id[:-1]
                decl.appendleft("const")
        else:
            if "context" in node.attrib:
                name = Util.full_name_of(node, root)
            else:
                name = node.attrib["name"]

            decl.appendleft(name)

            tp = Type(decl, node.tag)
            Registry.add(tp)

            return tp


_built_in = {
    "char": {
        "specifier": 'c',
        "builder": "PyLong_FromLong",
        "extractor": "_PyInt_AsInt",
        "checker": "PyInt_Check",
    },

    "unsigned char": {
        "specifier": 'B',
        "builder": "PyLong_FromUnsignedLong",
        "extractor": "PyInt_AsUnsignedLongMask",
        "checker": "PyInt_Check",
    },

    "short int": {
        "specifier": 'h',
        "builder": "PyLong_FromLong",
        "extractor": "_PyInt_AsInt",
        "checker": "PyInt_Check",
    },

    "short unsigned int": {
        "specifier": 'H',
        "builder": "PyLong_FromUnsignedLong",
        "extractor": "PyInt_AsUnsignedLongMask",
        "checker": "PyInt_Check",
    },

    "int": {
        "specifier": 'i',
        "builder": "PyLong_FromLong",
        "extractor": "_PyInt_AsInt",
        "checker": "PyInt_Check",
    },

    "unsigned int": {
        "specifier": 'I',
        "builder": "PyLong_FromUnsignedLong",
        "extractor": "PyInt_AsUnsignedLongMask",
        "checker": "PyInt_Check",
    },

    "long int": {
        "specifier": 'l',
        "builder": "PyLong_FromLong",
        "extractor": "PyInt_AS_LONG",
        "checker": "PyInt_Check",
    },

    "long unsigned int": {
        "specifier": 'k',
        "builder": "PyLong_FromUnsignedLong",
        "extractor": "PyInt_AsUnsignedLongMask",
        "checker": "PyInt_Check",
    },

    "float": {
        "specifier": 'f',
        "builder": "PyFloat_FromDouble",
        "extractor": "PyFloat_AS_DOUBLE",
        "checker": "PyFloat_Check",
    },

    "double": {
        "specifier": 'd',
        "builder": "PyFloat_FromDouble",
        "extractor": "PyFloat_AS_DOUBLE",
        "checker": "PyFloat_Check",
    },

    "bool": {
        "specifier": 'O',
        "builder": "PyBool_FromLong",
        "checker": "PyBool_Check",
    },

}


def extract_as_bool(pyobj):
    return "(PyObject_IsTrue(%s) == 1)" % pyobj


def _test():
    tp = Type(("long int",), "FundamentalType")

    print tp.get_build_value_idecl("x")
    print ""

    #-----------------------------------------------------------------------#

    tp = Type(("double", "const"), "FundamentalType")

    print tp.get_build_value_idecl("d")
    print ""

    #-----------------------------------------------------------------------#

    tp = Type(("double", "*",), "FundamentalType")

    print tp.get_build_value_idecl("dp")
    print tp.declate_var("dp2", "NULL")
    print ""

    #-----------------------------------------------------------------------#

    tp = Type(("float", "*", "*", "*", "const",), "FundamentalType")

    print tp.get_build_value_idecl("fp")
    print tp.declate_var("fp2", "NULL")
    print ""

    #-----------------------------------------------------------------------#

    tp = Type(("bool",), "FundamentalType")

    print tp.get_build_value_idecl("flag")
    print tp.declate_var("flag2", "false")
    
    #-----------------------------------------------------------------------#
    
    from Module import wxPythonNamer

    tp = Type(("wxSize", "const",), "Class")
    print tp.get_build_value_idecl("sz", namer=wxPythonNamer())


def _test_get_type_from_id():
    import xml.etree.ElementTree as ET
    root = ET.parse("wx.xml").getroot()

    print _is_function_pointer(_get_node_by_id("_13", root), root)
    print _is_function_pointer(_get_node_by_id("_19", root), root)
    print _is_function_pointer(_get_node_by_id("_14", root), root)

if __name__ == "__main__":
    _test_get_type_from_id()