
import Argument
import Code.Snippets
import CodeBlock
import Session
import Types


class TupleAndKeywords:
    def __init__(self):
        self.args = []
        self.unnamed_counter = 0

    def add_parameter(self, arg):
        assert isinstance(arg, Argument.Argument)

        if arg.defv is None and len(self.args) > 0:
            assert self.args[-1].defv is None

        if not arg.name:
            arg.name = "unnamed"
            if self.unnamed_counter > 0:
                arg.name += str(self.unnamed_counter)

                if self.unnamed_counter == 1:
                    self.args[0].name += '0'

            self.unnamed_counter += 1

        self.args.append(arg)

    def get_fmt_specifier(self):
        specifier = ""

        first_optional_processed = False
        for arg in self.args:
            if arg.defv is not None and not first_optional_processed:
                first_optional_processed = True
                specifier += '|'

            if not arg.type.cvt:
                specifier += arg.type.get_specifier()
            else:
                specifier += arg.type.cvt.specifier(arg.type)

        return specifier

    def get_parameters_string(self):
        return ", ".join([arg.name for arg in self.args])

    def get_keywords(self):
        return [arg.raw_name for arg in self.args]

    def clear(self):
        self.args = []

    def size(self):
        return len(self.args)

    def empty(self):
        return self.size() == 0

    def build_parser_idecl(self, namer=None, enable_kw=True, func_name=None):
        fmt = self.get_fmt_specifier()
        if func_name:
            fmt += ':' + func_name

        ptrs = ", ".join(self._build_parser_args(namer=namer))

        if enable_kw:
            idecl = Code.Snippets.PyArg_ParseTupleAndKeywords % {
                "TUPLE": "args",
                "KW_TUPLE": "kwargs",
                "KW_ARRAY": "keywords",
                "FORMAT": '"%s"' % fmt,
                "ARGS": ptrs,
            }
        else:
            idecl = Code.Snippets.PyArg_ParseTuple % {
                "TUPLE": "args",
                "FORMAT": '"%s"' % fmt,
                "ARGS": ptrs,
            }

        if idecl.endswith(", )"):
            idecl = idecl[:-3] + ')'

        return idecl

    def _build_parser_args(self, namer=None):
        result = []

        for arg in self.args:
            if arg.type.cvt:
                pytype = namer.pytype(arg.type.intrinsic_type())
                decl = arg.type.cvt.args_parsing_interim_vars(arg.type, arg.name, pytype)
            elif arg.type.is_built_in():
                decl = '&' + arg.name if not arg.type.is_bool() else "&py_" + arg.name
            elif arg.type.decl_no_const() == "PyObject *":
                decl = '&' + arg.name
            else:
                if not arg.type.is_ptr():
                    if arg.type.is_trivial():
                        result.append("&PyCapsule_Type")
                    else:
                        result.append('&' + namer.pytype(arg.type.intrinsic_type()))

                decl = "&py_" + arg.name

            result.append(decl)

        return result

    def write_args_parsing_code(self, block, namer, enable_kw, err_return, pyside_debug_name):
        error_handler_label = "__ARGS_PARSING_ERROR_HANDLER_" + str(block.size())
        require_error_handler_label = False

        to_cxx = []
        count0 = 0

        for arg in self.args:
            if arg.type.cvt:
                block.write_code(arg.type.cvt.args_parsing_declare_vars(arg.type, arg.name, arg.defv))

                goto_error_return = "goto %s;" % error_handler_label
                if arg.type.cvt.args_parsing_require_error_handling(arg.type):
                    require_error_handler_label = True

                extracting_code = arg.type.cvt.args_parsing_extracting_code(
                    arg.type, arg.name, arg.defv, goto_error_return, namer
                )

                if len(extracting_code) > 0:
                    to_cxx += extracting_code.split('\n')

                Session.header_jar().add_headers(arg.type.cvt.additional_headers(arg.type))
            elif arg.type.is_built_in():
                if arg.type.is_bool():
                    block.write_code("PyObject *py_%s = nullptr;" % arg.name)

                    if arg.defv is None:
                        extracting_code = Types.extract_as_bool("py_%s" % arg.name)
                        to_cxx.append(arg.type.declare_var(arg.name, extracting_code))
                    else:
                        to_cxx.append(arg.type.declare_var(arg.name, arg.defv))

                        extracting_code = (Code.Snippets.check_and_extract_as_bool % {
                            "VAR_NAME": arg.name
                        }).split('\n')

                        to_cxx += extracting_code
                else:
                    block.write_code(arg.type.declare_var(arg.name, arg.defv))
            elif arg.type.is_ref():
                if not arg.type.is_trivial():
                    pytype = namer.pytype(arg.type.intrinsic_type())
                    block.write_code("extern PyTypeObject %s;" % pytype)

                block.write_code("PyObject *py_%s = nullptr;" % arg.name)
                cpp_ptr_type = arg.type.ref_to_ptr()

                if arg.type.is_trivial():
                    capsule_ensure_reference = (Code.Snippets.capsule_ensure_reference % {
                        "VAR_NAME": arg.name,
                        "CAP_NAME": arg.type.decl_no_const(),
                        "ERROR_RETURN": "goto %s;" % error_handler_label,
                    }).split('\n')

                    require_error_handler_label = True

                    if arg.defv is None:
                        to_cxx += capsule_ensure_reference

                        init_expr = '*((%s) PyCapsule_GetPointer(py_%s, "%s"))' % (
                            (cpp_ptr_type.decl(), arg.name, arg.type.decl_no_const(),)
                        )

                        to_cxx.append(arg.type.declare_var(arg.name, init_expr))
                    else:
                        var_ptr = arg.name + "_ptr"  # TODO: more robust way
                        to_cxx.append(cpp_ptr_type.declare_var(var_ptr, "&(%s)" % arg.defv))

                        to_cxx.append("if (py_%s) {" % arg.name)
                        to_cxx.append(">>>")
                        to_cxx += capsule_ensure_reference
                        to_cxx.append(var_ptr + ' = (%s) PyCapsule_GetPointer(py_%s, "%s")' % (
                            cpp_ptr_type, arg.name, arg.type.decl_no_const(),
                        ))
                        to_cxx.append("<<<")
                        to_cxx.append("}")

                        to_cxx.append(arg.type.declare_var(arg.name, '*' + var_ptr))
                else:  # reference to class
                    if arg.defv is None:
                        init_expr = '*' + Code.Snippets.external_type_real_ptr % {
                            "CLASS": arg.type.intrinsic_type(),
                            "PYOBJ_PTR": "py_" + arg.name
                        }

                        to_cxx.append(arg.type.declare_var(arg.name, init_expr))
                    else:
                        var_ptr = arg.name + "_ptr"  # TODO:
                        to_cxx.append(cpp_ptr_type.declare_var(var_ptr, "&(%s)" % arg.defv))

                        to_cxx.append("if (py_%s) {" % arg.name)
                        to_cxx.append(">>>")
                        to_cxx.append(var_ptr + ' = ' + Code.Snippets.external_type_real_ptr % {
                            "CLASS": arg.type.intrinsic_type(),
                            "PYOBJ_PTR": "py_" + arg.name
                        } + ';')
                        to_cxx.append("<<<")
                        to_cxx.append("}")

                        to_cxx.append(arg.type.declare_var(arg.name, '*' + var_ptr))
            elif arg.type.decl_no_const() == "PyObject *":
                init_expr = "nullptr"
                if arg.defv is not None:
                    init_expr = arg.defv

                block.write_code(arg.type.declare_var(arg.name, init_expr))
            else:  # pointer or argument pass by value
                if arg.type.is_trivial():  # trivial pointer
                    pytype = "PyCapsule_Type"

                    block.write_code("PyObject *py_%s = nullptr;" % arg.name)
                    extracting_code = '(%s) PyCapsule_GetPointer(py_%s, "%s")' % (
                        (arg.type.decl(), arg.name, arg.type.decl_no_const(),)
                    )

                    to_cxx.append(arg.type.declare_var(arg.name, arg.defv if arg.defv else "nullptr"))
                else:
                    pytype = namer.pytype(arg.type.intrinsic_type())

                    block.write_code("extern PyTypeObject %s;" % pytype)
                    block.write_code("PyObject *py_%s = nullptr;" % arg.name)

                    extracting_code = Code.Snippets.external_type_real_ptr % {
                        "CLASS": arg.type.intrinsic_type(),
                        "PYOBJ_PTR": "py_" + arg.name
                    }

                    if not arg.type.is_ptr():  # args pass by value
                        extracting_code = '*' + extracting_code

                        if not arg.defv:
                            init_expr = extracting_code
                            extracting_code = None  # DONE processing
                        else:
                            init_expr = arg.defv

                        to_cxx.append(arg.type.declare_var(arg.name, init_expr))
                    else:
                        to_cxx.append(arg.type.declare_var(arg.name, "nullptr"))

                if arg.type.is_ptr() or arg.defv is not None:
                    memblock = CodeBlock.CodeBlock()

                    if arg.defv is not None:
                        memblock.write_code("if (py_%s) {" % arg.name)
                        memblock.indent()

                    if arg.type.is_ptr():
                        memblock.write_code("if (py_%s != Py_None) {" % arg.name)
                        memblock.indent()

                        memblock.write_code(Code.Snippets.extract_pointer % {
                            "VAR_NAME": arg.name, "PYTYPE": pytype,
                            "POINTER_TYPE": arg.type.intrinsic_type(),
                            "EXTRACTING_CODE": extracting_code,
                            "ERROR_HANDLER": "goto %s;" % error_handler_label,
                        })

                        require_error_handler_label = True

                        memblock.unindent()
                        memblock.write_code("}")
                    else:
                        memblock.write_code("%s = %s;" % (arg.name, extracting_code))

                    if arg.defv is not None:
                        memblock.unindent()
                        memblock.write_code('}')

                    to_cxx += memblock.lines

            if count0 < len(to_cxx):
                to_cxx.append("")
                count0 = len(to_cxx)

        if enable_kw:
            kws = "nullptr"
            if not self.empty():
                kws = ", ".join(['"%s"' % kw for kw in self.get_keywords()] + ["nullptr"])

            block.write_code("const char *keywords[] = { %s };" % kws)
            block.append_blank_line()

        parser_idecl = self.build_parser_idecl(namer=namer, enable_kw=enable_kw,
                                               func_name=pyside_debug_name)

        block.write_error_check("!" + parser_idecl, handler=err_return,
                                handler_label=error_handler_label if require_error_handler_label else None)

        block.append_blank_line()
        if len(to_cxx) > 0:
            block.write_lines(to_cxx)

    def build_function_signature_parameter_list(self):
        return ", ".join([a.type.join_type_and_name(a.name) for a in self.args])

    def build_parameter_type_only_list(self):
        return ", ".join([a.type.decl() for a in self.args])


def test_empty():
    tk = TupleAndKeywords()

    print tk.get_keywords()
    print tk.build_parser_idecl()

    assert len(tk.build_function_signature_parameter_list()) == 0


def test_fundamental():
    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("int",), 1, "FundamentalType"), "foo", 10))
    tk.add_parameter(Argument.Argument(Types.Type(("long int",), 2, "FundamentalType"), "bar", 20))
    tk.add_parameter(Argument.Argument(Types.Type(("int",), 3, "FundamentalType"), "mit", 30))

    print tk.get_fmt_specifier()
    print tk.get_keywords()
    print tk.build_parser_idecl()
    print tk.build_function_signature_parameter_list()


def test():
    from Console.wxMSW.__wx__ import WxPythonNamer

    import Converters
    import HeaderJar
    import CodeBlock

    header_jar = HeaderJar.HeaderJar()
    Session.begin(header_jar)

    Converters.add(Converters.WcsConv())

    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("int", "*",), 1, "FundamentalType"), "foo"))
    tk.add_parameter(Argument.Argument(Types.Type(("double", "&",), 2, "FundamentalType"), "bar"))
    tk.add_parameter(Argument.Argument(Types.Type(("long unsigned int", "&", "const",), 3, "FundamentalType"), "xyz"))
    tk.add_parameter(Argument.Argument(Types.Type(("X", "const", "&",), 4, "Class"), "x"))
    tk.add_parameter(Argument.Argument(Types.Type(("Y", "*",), 5, "Class"), "y"))
    tk.add_parameter(Argument.Argument(Types.Type(("Z",), 6, "Class"), "z"))
    tk.add_parameter(Argument.Argument(Types.Type(("bool",), 7, "FundamentalType"), "b"))
    tk.add_parameter(Argument.Argument(Types.Type(("wchar_t", "const", "*",), 8, "PointerType"), "str"))

    print tk.get_fmt_specifier()
    print tk.get_keywords()
    print tk.build_function_signature_parameter_list()

    namer = WxPythonNamer()

    print tk.build_parser_idecl(namer=namer)
    empty_line()

    block = CodeBlock.CodeBlock()
    tk.write_args_parsing_code(block, namer, True, "return nullptr;", "<TEST>")

    print block.flush()
    empty_line()
    empty_line()

    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("int", "*",), 1, "FundamentalType"), "foo", "nullptr"))
    tk.add_parameter(Argument.Argument(Types.Type(("double", "&",), 2, "FundamentalType"), "bar", "PI"))
    tk.add_parameter(Argument.Argument(Types.Type(("long unsigned int", "&", "const",), 3, "FundamentalType"), "xyz", "MAXINT"))
    tk.add_parameter(Argument.Argument(Types.Type(("X", "const", "&",), 4, "Class"), "x", "_x"))
    tk.add_parameter(Argument.Argument(Types.Type(("Y", "*",), 5, "Class"), "y", "_py"))
    tk.add_parameter(Argument.Argument(Types.Type(("Z",), 6, "Class"), "z", "Z(1990)"))
    tk.add_parameter(Argument.Argument(Types.Type(("bool",), 7, "FundamentalType"), "b", "true"))
    tk.add_parameter(Argument.Argument(Types.Type(("wchar_t", "const", "*",), 8, "PointerType"), "str", 'L"Hello world!"'))
    tk.write_args_parsing_code(block, namer, True, "return nullptr;", "<TEST>")

    print block.flush()

    integer = Types.Type(("int",), 99, "FundamentalType")
    Converters.add(Converters.ListConv(integer))

    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("std::vector<int>", "const", "&",), 0, "Class"), "vi", "_vi"))
    tk.write_args_parsing_code(block, namer, True, "return nullptr;", "<TEST>")

    print block.flush()

    K = Types.Type(("wchar_t", "const", "*",), 111, "PointerType")
    V = Types.Type(("wxColour", "*",), 112, "PointerType")
    Converters.add(Converters.DictConv(K, V))

    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("std::map<wchar_t const *, wxColour *>", "&",), 0, "Class"), "m"))
    tk.write_args_parsing_code(block, namer, True, "return nullptr;", "<TEST>")

    print block.flush()


def empty_line():
    print ""

if __name__ == "__main__":
    test_empty()

    empty_line()
    test_fundamental()

    empty_line()
    test()
