from collections import deque

import Code.Snippets
import CodeBlock
import Converters
import Session
import Util


BUILT_IN = 1
REFERENCE = 2
POINTER = 3
CLASS = 4


class Type:
    def __init__(self, decl_list, tid, tag):
        assert isinstance(decl_list, (list, tuple, deque,))
        assert len(decl_list) > 0
        assert isinstance(tid, int)
        assert isinstance(tag, str)

        self.decl_list = decl_list
        self.decl_list_no_const = [d for d in decl_list if d != "const"]
        self.tid = tid
        self.tag = tag

        self.cvt = Converters.find(self)

    def __str__(self):
        return self.decl()

    def decl(self):
        return self._decl(self.decl_list)

    def decl_no_const(self):
        return self._decl(self.decl_list_no_const)

    def _decl(self, decl_list):
        if self.is_function_pointer():
            return "__FP_%d" % self.tid

        return self._fmt(' '.join(decl_list))

    @staticmethod
    def _fmt(decl):
        return decl.replace("* ", "*").replace("& ", "&")

    def intrinsic_type(self):
        return self.decl_list[0]

    def has_decorators(self):
        return len(self.decl_list) > 1

    def typedef(self, typename):
        if self.is_function_pointer():
            return "typedef %s;" % typename.join(self.decl_list)
        else:
            return "typedef %s;" % self.declare_var(typename)

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

    def is_function_pointer(self):
        return self.tag in ("FunctionType", "MethodType")

    def is_ptr_or_ref(self):
        return self.is_ref() or self.is_ptr()

    def is_ptr(self):
        return self.decl_list_no_const[-1] == '*' or self.is_function_pointer()

    def is_ref(self):
        return self.decl_list_no_const[-1] == '&'

    def is_built_in(self):
        return self.is_enum() or (
            len(self.decl_list_no_const) == 1 and
            self.decl_list_no_const[0] in _built_in
        )

    def is_trivial(self):
        if self.is_built_in():
            return True

        if self.is_function_pointer():
            return True

        if self.is_ptr_or_ref():
            secondary_decl = self.decl_list_no_const[-2]
            if secondary_decl in _built_in or secondary_decl in "&*":
                return True

        return False

    def is_pyobject_ptr(self):
        return self.decl_no_const() == "PyObject *"

    def is_class_value(self):
        return not self.is_ptr_or_ref() and not self.is_trivial()

    def is_const(self):
        if self.decl_list[-1] == "const":
            return True

        if len(self.decl_list) >= 3:
            if self.decl_list[-2] == "const" and self.decl_list[-1] in ("&", "*",):
                return True

        return False

    def ref_to_ptr(self):
        assert self.is_ptr_or_ref()

        ret = [oper for oper in self.decl_list]
        for index, oper in enumerate(ret):
            if oper == '&':
                ret[index] = '*'
                break

        return Type(ret, self.tid, self.tag)

    def get_specifier(self):
        if self.is_built_in():
            if self.is_enum():
                return 'i'
            else:
                return _built_in[self.decl_no_const()]["specifier"]
        else:
            return "O" if self.is_ptr() else "O!"

    def join_type_and_name(self, name, strip_last_const=False):
        decl = self.decl()

        if strip_last_const:
            if decl.endswith("const") and decl[-6] in "*& ":
                decl = decl[:((-5) if decl[-6] != ' ' else (-6))]

        if decl[-1] in "&*":
            return decl + name
        else:
            return "%s %s" % (decl, name)

    def declare_var(self, name, init=None, strip_last_const=True):
        decl = self.join_type_and_name(name, strip_last_const)

        if init is not None:
            if self.category() == CLASS:
                return decl + "(%s);" % init
            else:
                if self.is_enum():
                    intrinsic = self.intrinsic_type()
                    pos = intrinsic.rfind("::")
                    if pos != -1:
                        ns = intrinsic[:(pos + 2)]
                        init = ns + init

                return decl + " = %s;" % init
        else:
            return decl + ";"

    def get_build_value_idecl(self, var_name, py_var_name=None, namer=None, raii=False):
        assert not self.is_pyobject_ptr()

        if py_var_name is None:
            if '.' in var_name:
                intrinsic_name = var_name[(var_name.rindex('.') + 1):]
            elif "->" in var_name:
                intrinsic_name = var_name[(var_name.rindex('>') + 1):]
            else:
                intrinsic_name = var_name

            py_var_name = "py_" + intrinsic_name

        if self.cvt:
            Session.header_jar().add_headers(self.cvt.additional_headers(self))
            return self.cvt.build(self, var_name, py_var_name, namer, raii)
        elif self.is_built_in():
            if self.is_enum():
                builder = _built_in["int"]["builder"]
            else:
                builder = _built_in[self.decl_no_const()]["builder"]

            if raii:
                return "PyObjectPtr %s(%s(%s));" % (py_var_name, builder, var_name)
            else:
                return "PyObject *%s = %s(%s);" % (py_var_name, builder, var_name)
        elif self.is_ptr_or_ref():
            if self.is_ref():
                ptr = "&%s" % var_name if var_name.isalnum() else "&(%s)" % var_name
                ref = var_name
            else:
                ptr = var_name
                ref = "*%s" % var_name if var_name.isalnum() else "*(%s)" % var_name

            if self.is_trivial():
                template_args = {
                    "VAR": ptr,
                    "PY_VAR_NAME": py_var_name,
                    "TYPE_STR": self.decl_no_const(),
                }

                if raii:
                    return Code.Snippets.PyCapsule_New_RAII % template_args
                else:
                    return Code.Snippets.PyCapsule_New % template_args
            else:
                assert namer is not None

                boilerplate = Code.Snippets.borrow_from_ptr
                if self.is_ref():
                    if raii:
                        boilerplate = Code.Snippets.borrow_from_ref_raii
                    else:
                        boilerplate = Code.Snippets.borrow_from_ref

                ret = boilerplate % {
                    "VAR": var_name,
                    "PY_VAR_NAME": py_var_name,
                    "PTR": ptr, "REF": ref,
                    "CLASS": self.intrinsic_type(),
                    "BORROWER": namer.borrower(self.intrinsic_type()),
                }

                if self.is_ptr():
                    if raii:
                        ret += "\nPyObjectPtr %s(%s_raw);" %(py_var_name, py_var_name)
                    else:
                        ret += "\nPyObject *%s = %s_raw;" %(py_var_name, py_var_name)

                return ret
        else:
            assert namer is not None

            boilerplate = Code.Snippets.copy_raii if raii else Code.Snippets.copy
            return boilerplate % {
                "VAR": var_name, "PY_VAR_NAME": py_var_name,
                "CLASS": self.intrinsic_type(),
                "COPYER": namer.copyer(self.intrinsic_type()),
            }

    def get_extractor_code(self, var_name, py_var_name, error_return, namer=None):
        block = CodeBlock.CodeBlock()

        if self.is_ptr():
            block.write_code(self.declare_var(var_name, "nullptr"))
            block.write_code("if (%s != Py_None) {" % py_var_name)
            block.indent()

        if self.cvt is not None:
            Session.header_jar().add_headers(self.cvt.additional_headers(self))

            negative_checker = self.cvt.negative_checker(self, "(PyObject *) " + py_var_name)
            extracting_code = self.cvt.extracting_code(self, var_name, py_var_name, error_return, namer)
        elif self.is_built_in():
            if self.is_enum():
                dummy_type = "int"
            else:
                dummy_type = self.decl_no_const()

            negative_checker = "!%s((PyObject *) %s)" % (_built_in[dummy_type]["checker"], py_var_name)

            if self.is_bool():
                extracting_code = self.declare_var(var_name, extract_as_bool(py_var_name))
            else:
                extracting_code = Code.Snippets.extract_builtin_type % {
                    "CAST_ENUM": "(%s) " % self.decl() if self.is_enum() else "",
                    "EXTRACTOR": _built_in[dummy_type]["extractor"],
                    "VAR_TYPE": self.decl(),
                    "PY_VAR_NAME": py_var_name,
                    "VAR_NAME": var_name,
                }
        elif self.is_trivial():
            negative_checker = '!PyCapsule_IsValid(%s, "%s")' % (
                py_var_name, self.decl_no_const(),
            )

            extracting_code = '%s = (%s) PyCapsule_GetPointer(%s, "%s");' % (
                var_name, self.decl(), py_var_name, self.decl_no_const(),
            )
        else:
            pytype = namer.pytype(self.intrinsic_type())
            block.write_code("extern PyTypeObject %s;" % pytype)

            negative_checker = "!PyObject_TypeCheck(%s, &%s)" % (py_var_name, pytype)

            if not self.is_ptr():
                extracting_code = self.declare_var(var_name,
                    '*' + Code.Snippets.external_type_real_ptr % {
                        "CLASS": self.intrinsic_type(),
                        "PYOBJ_PTR": py_var_name,
                    })
            else:
                extracting_code = (var_name + " = " +
                   Code.Snippets.external_type_real_ptr % {
                        "CLASS": self.intrinsic_type(),
                        "PYOBJ_PTR": py_var_name,
                    } + ';')

        block.write_code(Code.Snippets.single_var_extractor % {
            "NEGATIVE_CHECKER": negative_checker,
            "VAR_TYPE": self.decl(),
            "PY_VAR_NAME": py_var_name,
            "VAR_NAME": var_name,
            "ERROR_RETURN": error_return,
            "EXTRACTING_CODE": extracting_code,
        })

        if self.is_ptr():
            block.unindent()
            block.write_code('}')

        return block.flush()


class PythonAwareClassRegistry:

    _registry = {}

    def __init__(self):
        pass

    @staticmethod
    def add(cls_name, interfaces):
        PythonAwareClassRegistry._registry[cls_name] = interfaces

    @staticmethod
    def find(cls_name):
        return PythonAwareClassRegistry._registry.get(cls_name)


def _get_node_by_id(node_id, root):
    return root.find(".//*[@id='%s']" % node_id)


def _flatize_function_pointer(node, root):
    returns = get_type_by_id(node.attrib["returns"], root)

    if "basetype" in node.attrib:
        tp = get_type_by_id(node.attrib["basetype"], root)
        basetype = tp.decl() + "::"
    else:
        basetype = ""

    if "const" in node.attrib:
        const = " const"
    else:
        const = ""

    args = []
    for arg in node.findall("Argument"):
        args.append(get_type_by_id(arg.attrib["type"], root))

    decl_list = ("%s (%s*" % (returns.decl(), basetype),
                 ")(%s)%s" % (", ".join([arg.decl() for arg in args]), const))

    return decl_list


def _try_as_function_pointer(node_id, root):
    node = _get_node_by_id(node_id, root)

    if node is None:
        msg = "Fatal error: no XML node with id `%s` found!" % node_id
        raise Exception(msg)

    while "type" in node.attrib:
        node = _get_node_by_id(node.attrib["type"], root)

    if node.tag in ("FunctionType", "MethodType"):
        decl_list = _flatize_function_pointer(node, root)
        tid = int(node.attrib["id"][1:])

        return Type(decl_list, tid, node.tag)
    else:
        return None


def get_type_by_id(type_node_id, root):
    assert isinstance(type_node_id, str)
    assert root is not None

    decl = deque()

    tp = _try_as_function_pointer(type_node_id, root)

    while not tp:
        node = _get_node_by_id(type_node_id, root)

        if type_node_id.endswith('c'):
            decl.appendleft("const")
        elif "name" not in node.attrib or node.tag == "Typedef":
            if node.tag == "ReferenceType":
                decl.appendleft('&')
            elif node.tag == "PointerType":
                decl.appendleft('*')
            elif node.tag == "ArrayType":
                if len(decl) > 0 and decl[0] == "const":
                    decl.popleft()
                    decl.appendleft('*')
                    decl.appendleft("const")
                else:
                    decl.appendleft('*')
        else:
            if "context" in node.attrib:
                name = Util.full_name_of(node, root)
            else:
                name = node.attrib["name"]

            decl.appendleft(name)

            tp = Type(decl, int(node.attrib["id"][1:]), node.tag)
            break

        type_node_id = node.attrib["type"]

    return tp


def declaring_to_assigning(tp, var_name, code):
    decl = tp.join_type_and_name(var_name)
    pos = code.rindex(decl) + len(decl)

    if code[pos] == ';':
        pos += 2
        beg = pos - len(decl)
        while beg > 0 and code[beg] != '\n':
            beg -= 1

        return code[:beg] + code[pos:]
    elif code[pos:].startswith(" = "):
        repl = var_name
    else:
        repl = var_name + " = "

    pos -= len(decl)
    return code[:pos] + code[pos:].replace(decl, repl)


_built_in = {
    "char": {
        "specifier": 'c',
        "builder": "PyInt_FromSize_t",
        "extractor": "pbpp::Types::ToChar",
        "checker": "pbpp::Types::IsNumber",
    },

    "unsigned char": {
        "specifier": 'B',
        "builder": "PyInt_FromSize_t",
        "extractor": "pbpp::Types::ToUnsignedChar",
        "checker": "pbpp::Types::IsNumber",
    },

    "wchar_t": {
        "specifier": 'I',
        "builder": "PyInt_FromSize_t",
        "extractor": "pbpp::Types::ToWChar",
        "checker": "pbpp::Types::IsNumber",
    },

    "short int": {
        "specifier": 'h',
        "builder": "PyInt_FromSsize_t",
        "extractor": "pbpp::Types::ToShort",
        "checker": "pbpp::Types::IsNumber",
    },

    "short unsigned int": {
        "specifier": 'H',
        "builder": "PyInt_FromSize_t",
        "extractor": "pbpp::Types::ToUnsignedShort",
        "checker": "pbpp::Types::IsNumber",
    },

    "int": {
        "specifier": 'i',
        "builder": "PyInt_FromSsize_t",
        "extractor": "pbpp::Types::ToInt",
        "checker": "pbpp::Types::IsNumber",
    },

    "unsigned int": {
        "specifier": 'I',
        "builder": "PyInt_FromSize_t",
        "extractor": "pbpp::Types::ToUnsignedInt",
        "checker": "pbpp::Types::IsNumber",
    },

    "long int": {
        "specifier": 'l',
        "builder": "PyLong_FromLong",
        "extractor": "pbpp::Types::ToLong",
        "checker": "pbpp::Types::IsNumber",
    },

    "long unsigned int": {
        "specifier": 'k',
        "builder": "PyLong_FromUnsignedLong",
        "extractor": "pbpp::Types::ToUnsignedLong",
        "checker": "pbpp::Types::IsNumber",
    },

    "long long int": {
        "specifier": 'L',
        "builder": "PyLong_FromLongLong",
        "extractor": "pbpp::Types::ToLongLong",
        "checker": "pbpp::Types::IsNumber",
    },

    "long long unsigned int": {
        "specifier": 'L',
        "builder": "PyLong_FromUnsignedLongLong",
        "extractor": "pbpp::Types::ToUnsignedLongLong",
        "checker": "pbpp::Types::IsNumber",
    },

    "float": {
        "specifier": 'f',
        "builder": "PyFloat_FromDouble",
        "extractor": "pbpp::Types::ToDouble",
        "checker": "pbpp::Types::IsNumber",
    },

    "double": {
        "specifier": 'd',
        "builder": "PyFloat_FromDouble",
        "extractor": "pbpp::Types::ToDouble",
        "checker": "pbpp::Types::IsNumber",
    },

    "bool": {
        "specifier": 'O',
        "builder": "PyBool_FromLong",
        "checker": "PyBool_Check",
    },

    "void": {

    },
}

# `signed char` is another type different with `char`
_built_in["signed char"] = _built_in["char"]


def extract_as_bool(pyobj):
    return "(PyObject_IsTrue(%s) == 1)" % pyobj
