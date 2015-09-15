
import CodeBlock
import Code.Snippets
import Types

_converters = []


class Converter:
    def __init__(self):
        pass

    def match(self, cpp_type):
        return False

    def additional_headers(self, cpp_type):
        return ()

    def specifier(self, cpp_type):
        return "O"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        return '\n'.join(("PyObject *py_%s = nullptr;" % var_name,
            cpp_type.declare_var(var_name, defv),
        ))

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        return "&py_%s" % arg_name

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        raise NotImplementedError()

    def args_parsing_require_error_handling(self, cpp_type):
        return True

    def negative_checker(self, cpp_type, py_var_name):
        raise NotImplementedError()

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        raise NotImplementedError()

    def value_building_interim_var(self, arg_name):
        return arg_name

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        raise NotImplementedError()


def add(cvt):
    assert isinstance(cvt, Converter)
    _converters.append(cvt)


def find(cpp_type):
    for cvt in _converters:
        if cvt.match(cpp_type):
            return cvt

    return None


class StrConv(Converter):
    def __init__(self):
        Converter.__init__(self)

    def match(self, cpp_type):
        return cpp_type.decl() in ("char const *", "const char *",)

    def specifier(self, cpp_type):
        return "s"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        init_expr = "nullptr" if defv is None else defv
        return cpp_type.declare_var(var_name, init_expr)

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        return '&' + arg_name

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        return ""

    def args_parsing_require_error_handling(self, cpp_type):
        return False

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyString_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        return var_name + " = PyString_AsString(%s);" % py_var_name

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        if raii:
            return "PyObjectPtr %s(PyString_FromString(%s));" % (py_var_name, var_name)
        else:
            return "PyObject *%s = PyString_FromString(%s);" % (py_var_name, var_name)


class WcsConv(Converter):
    def __init__(self):
        Converter.__init__(self)

    def match(self, cpp_type):
        return cpp_type.decl() in ("wchar_t const *", "const wchar_t *",)

    def specifier(self, cpp_type):
        return "u"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        init_expr = "nullptr"
        if defv is not None:
            init_expr = "(%s) " % cpp_type.decl() + defv

        return cpp_type.declare_var(var_name, init_expr)

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        return '&' + arg_name

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        return ""

    def args_parsing_require_error_handling(self, cpp_type):
        return False

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyUnicode_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        return var_name + " = PyUnicode_AsUnicode(%s);" % py_var_name

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        if raii:
            return "PyObjectPtr %s(PyUnicode_FromWideChar(%s, wcslen(%s)));" % (
                py_var_name, var_name, var_name
            )
        else:
            return "PyObject *%s = PyUnicode_FromWideChar(%s, wcslen(%s));" % (
                py_var_name, var_name, var_name
            )


class ContainerConv(Converter):
    def __init__(self, real_pytype):
        Converter.__init__(self)
        self.real_pytype = real_pytype

    @staticmethod
    def reference_type(cpp_type):
        if cpp_type.is_const():
            if cpp_type.is_ptr():
                return "CONST_PTR"
            elif cpp_type.is_ref():
                return "CONST_REF"
            else:
                return "CONST_VALUE"
        else:
            if cpp_type.is_ptr():
                return "PTR"
            elif cpp_type.is_ref():
                return "REF"
            else:
                return "VALUE"

    def specifier(self, cpp_type):
        return "O!" if not cpp_type.is_ptr() else "O"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        return "PyObject *py_%s = nullptr;" % var_name

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        interim_vars = []
        if not cpp_type.is_ptr():
            interim_vars.append('&' + self.real_pytype)

        interim_vars.append("&py_" + arg_name)
        return ", ".join(interim_vars)


class ListConv(ContainerConv):
    def __init__(self, T):
        ContainerConv.__init__(self, "PyList_Type")
        self.T = T

    def match(self, cpp_type):
        if not cpp_type.is_trivial():
            intrinsic_type = cpp_type.intrinsic_type().replace(' ', "")
            needle = "std::vector<" + self.T.decl().replace(' ', "")

            if intrinsic_type.startswith(needle):
                if not intrinsic_type[len(needle)].isalpha():
                    return True

        return False

    def additional_headers(self, cpp_type):
        return "_List.hxx",

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        reference_type = self.reference_type(cpp_type)
        should_write_back = reference_type in ("REF", "PTR",)
        py_var_name = "py_" + arg_name

        block = CodeBlock.CodeBlock()

        if cpp_type.is_ptr():
            conditions = []
            if defv is not None:
                conditions.append(py_var_name)

            conditions.append(py_var_name + " != Py_None")
            conditions.append(self.negative_checker(cpp_type, py_var_name))

            block.write_error_check(" && ".join(conditions), error_return)

        container_type = Types.Type((cpp_type.intrinsic_type(),), 0, "Class")

        extractor = self.T.get_extractor_code("item", "py_item", "return false;", namer)
        extractor = Types.declaring_to_assigning(self.T, "item", extractor)
        extractor += "\nreturn true;"

        pyobject_type = Types.Type(("PyObject", "*",), 0, "PointerType")

        if should_write_back:
            builder = self.T.get_build_value_idecl("item", "py_item", namer)
            builder = Types.declaring_to_assigning(pyobject_type, "py_item", builder)
            builder += "\nreturn true;"
        else:
            builder = "return false;"

        if defv is not None:
            set_defv = "%s.SetDefault(%s);\n" % (arg_name, defv)
        else:
            set_defv = ""

        block.write_code(Code.Snippets.extract_container % {
            "CONTAINER_TYPE": container_type.decl(),
            "ITEM_TYPE": self.T.decl(),
            "SPACE": "" if self.T.is_ptr() else " ",
            "VAR_NAME": arg_name,
            "PY_VAR_NAME": py_var_name,
            "REFERENCE_TYPE": reference_type,
            "BUILDER": builder,
            "EXTRACTOR": extractor,
            "SET_DEFAULT_VALUE": set_defv,
            "ERROR_RETURN": error_return,
        })

        return block.flush()

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyList_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        extract_and_assign = self.T.get_extractor_code("item", "py_item", error_return, namer)
        extract_and_assign += '\n' + var_name + ".push_back(item);"

        dummy_type = Types.Type((cpp_type.intrinsic_type(),), 0, "Class")
        decl_var = dummy_type.declare_var(var_name)

        return decl_var + '\n' + Code.Snippets.extract_sequence % {
            "VAR_NAME": var_name, "PY_VAR_NAME": py_var_name,
            "ITEM_EXTRACTING_CODE": extract_and_assign,
        }

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        item_building_code = self.T.get_build_value_idecl(
            var_name + "[i]", py_var_name="py_item", namer=namer
        )

        boilerplate = Code.Snippets.build_list_raii if raii else Code.Snippets.build_list
        return boilerplate % {
            "PY_VAR_NAME": py_var_name,
            "SIZE_TYPE": cpp_type.intrinsic_type() + "::size_type",
            "COUNT": var_name + ".size()",
            "ITEM_BUILDING_CODE": item_building_code,
        }


class DictConv(ContainerConv):
    def __init__(self, K, V):
        ContainerConv.__init__(self, "PyDict_Type")
        self.K = K
        self.V = V

    def match(self, cpp_type):
        if not cpp_type.is_trivial():
            intrinsic_type = cpp_type.intrinsic_type().replace(' ', "")
            needle = "std::map<%s,%s" % (self.K.decl(), self.V.decl())
            needle = needle.replace(' ', "")

            if intrinsic_type.startswith(needle):
                if not intrinsic_type[len(needle)].isalpha():
                    return True

        return False

    def additional_headers(self, cpp_type):
        return "_Dict.hxx",

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        reference_type = self.reference_type(cpp_type)
        should_write_back = reference_type in ("REF", "PTR",)
        py_var_name = "py_" + arg_name

        block = CodeBlock.CodeBlock()

        if cpp_type.is_ptr():
            conditions = []
            if defv is not None:
                conditions.append(py_var_name)

            conditions.append(py_var_name + " != Py_None")
            conditions.append(self.negative_checker(cpp_type, py_var_name))

            block.write_error_check(" && ".join(conditions), error_return)

        container_type = Types.Type((cpp_type.intrinsic_type(),), 0, "Class")
        pyobject_type = Types.Type(("PyObject", "*",), 0, "PointerType")

        key_extractor = self.K.get_extractor_code("key", "py_key", "return false;", namer)
        key_extractor = Types.declaring_to_assigning(self.K, "key", key_extractor)
        key_extractor += "\nreturn true;"

        if should_write_back:
            key_builder = self.K.get_build_value_idecl("key", "py_key", namer)
            key_builder = Types.declaring_to_assigning(pyobject_type, "py_key", key_builder)
            key_builder += "\nreturn true;"
        else:
            key_builder = "return false;"

        val_extractor = self.V.get_extractor_code("val", "py_val", "return false;", namer)
        val_extractor = Types.declaring_to_assigning(self.V, "val", val_extractor)
        val_extractor += "\nreturn true;"

        if should_write_back:
            val_builder = self.V.get_build_value_idecl("val", "py_val", namer)
            val_builder = Types.declaring_to_assigning(pyobject_type, "py_val", val_builder)
            val_builder += "\nreturn true;"
        else:
            val_builder = "return false;"

        if defv is not None:
            set_defv = "%s.SetDefault(%s);\n" % (arg_name, defv)
        else:
            set_defv = ""

        block.write_code(Code.Snippets.extract_dict % {
            "CONTAINER_TYPE": container_type.decl(),
            "KEY_TYPE": self.K.decl(),
            "K_SPACE": "" if self.K.is_ptr() else " ",
            "VALUE_TYPE": self.V.decl(),
            "V_SPACE": "" if self.V.is_ptr() else " ",
            "VAR_NAME": arg_name,
            "PY_VAR_NAME": py_var_name,
            "REFERENCE_TYPE": reference_type,
            "KEY_BUILDER": key_builder,
            "KEY_EXTRACTOR": key_extractor,
            "VALUE_BUILDER": val_builder,
            "VALUE_EXTRACTOR": val_extractor,
            "SET_DEFAULT_VALUE": set_defv,
            "ERROR_RETURN": error_return,
        })

        return block.flush()

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyDict_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        extracting_code = self.K.get_extractor_code("key", "py_dict_key", error_return, namer) + '\n'
        extracting_code += self.K.get_extractor_code("value", "py_dict_value", error_return, namer)

        dummy_type = Types.Type((cpp_type.intrinsic_type(),), 0, "Class")
        decl_var = dummy_type.declare_var(var_name)

        return decl_var + '\n' + Code.Snippets.simple_extract_dict % {
            "VAR_NAME": var_name, "PY_VAR_NAME": py_var_name,
            "KEY_TYPE": self.K.decl(),
            "VALUE_TYPE": self.V.decl(),
            "KV_EXTRACTING_CODE": extracting_code,
        }

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        key_building_code = self.K.get_build_value_idecl(
            "kv.first", py_var_name="py_dict_key", namer=namer
        )

        val_building_code = self.V.get_build_value_idecl(
            "kv.second", py_var_name="py_dict_value", namer=namer
        )

        boilerplate = Code.Snippets.build_dict_raii if raii else Code.Snippets.build_dict
        return boilerplate % {
            "VAR_NAME": var_name, "PY_VAR_NAME": py_var_name,
            "KEY_BUILDING_CODE": key_building_code,
            "VAL_BUILDING_CODE": val_building_code,
        }
