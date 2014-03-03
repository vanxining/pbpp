
import Argument
import Code.Snippets
import Types


class TupleAndKeywords:
    def __init__(self):
        self.args = []

    def add_parameter(self, arg):
        assert isinstance(arg, Argument.Argument)

        if arg.defv is None and len(self.args) > 0:
            assert self.args[-1].defv is None
        
        self.args.append(arg)

    def get_fmt_specifier(self):
        specifier = ""

        first_optional_processed = False
        for a in self.args:
            if a.defv is not None and not first_optional_processed:
                first_optional_processed = True
                specifier += '|'

            specifier += a.type.get_specifier()

        return specifier

    def get_parameters_string(self):
        return ", ".join(self.get_keywords())

    def get_keywords(self):
        return [arg.name for arg in self.args]

    def clear(self):
        self.args = []

    def size(self):
        return len(self.args)

    def empty(self):
        return self.size() == 0

    def build_parser_idecl(self, namer=None,
                           enable_kw=True,
                           args_tuple="args",
                           kwargs_tuple="kwargs",
                           kw_array="keywords",
                           func_name=None):
        fmt = self.get_fmt_specifier()
        if func_name:
            fmt += ':' + func_name

        ptrs = ", ".join(self._build_parser_args(parse=True, namer=namer))

        if enable_kw:
            idecl = Code.Snippets.PyArg_ParseTupleAndKeywords % {
                "TUPLE": args_tuple,
                "KW_TUPLE": kwargs_tuple,
                "KW_ARRAY": kw_array,
                "FORMAT": '"%s"' % fmt,
                "ARGS": ptrs,
            }
        else:
            idecl = Code.Snippets.PyArg_ParseTuple % {
                "TUPLE": args_tuple,
                "FORMAT": '"%s"' % fmt,
                "ARGS": ptrs,
            }

        if idecl.endswith(", )"):
            idecl = idecl[:-3] + ')'

        return idecl

    def _build_parser_args(self, parse=True, namer=None):
        result = []
        for a in self.args:
            if a.type.is_built_in():
                decl = a.name if not a.type.is_bool() else "py_" + a.name
                if parse:
                    decl = '&' + decl

                result.append(decl)
            else:
                if a.type.is_trivial():
                    result.append("&PyCapsule_Type")
                else:
                    assert namer
                    result.append('&' + namer.pytype(a.type.intrinsic_type()))

                result.append("&py_" + a.name)

        return result

    def write_args_parsing_code(self, namer, block, err_return,
                                enable_kw=True, args_tuple="args", kwargs_tuple="kwargs",
                                pyside_debug_name=None):
        to_cxx = []

        for arg in self.args:
            if arg.type.is_built_in():
                if arg.type.is_bool():
                    block.write_code("PyObject *py_%s;" % arg.name)

                    extracted = Types.extract_as_bool("py_%s" % arg.name)
                    to_cxx.append(arg.type.declate_var(arg.name, extracted))
                else:
                    block.write_code(arg.type.declate_var(arg.name, arg.defv))
            else:
                if arg.type.is_trivial():
                    block.write_code("PyObject *py_%s;" % arg.name)

                    if arg.type.is_ref():
                        ptr = arg.type.ref_to_ptr()
                        extracted = '*((%s) PyCapsule_GetPointer(py_%s, "%s"))' % (
                            (ptr.decl(), arg.name, arg.type.decl_no_const(),)
                        )
                    else:
                        extracted = '(%s) PyCapsule_GetPointer(py_%s, "%s")' % (
                            (arg.type.decl(), arg.name, arg.type.decl_no_const(),)
                        )
                else:
                    pytype = namer.pytype(arg.type.intrinsic_type())

                    block.write_code("extern PyTypeObject %s;" % pytype)
                    block.write_code("PyObject *py_%s;" % arg.name)

                    extracted = Code.Snippets.cast_external % {
                        "CLASS": arg.type.intrinsic_type(),
                        "PYOBJ_PTR": "py_" + arg.name
                    }

                    if not arg.type.is_ptr():
                        extracted = '*' + extracted

                to_cxx.append(arg.type.declate_var(arg.name, extracted))

        if enable_kw:
            kws = "NULL"
            if not self.empty():
                kws = ", ".join(['"%s"' % kw for kw in self.get_keywords()] + ["NULL"])

            block.write_code("const char *keywords[] = { %s };" % kws)
            block.append_blank_line()

        parser_idecl = self.build_parser_idecl(namer=namer, enable_kw=enable_kw,
                                               args_tuple=args_tuple, kwargs_tuple=kwargs_tuple,
                                               func_name=pyside_debug_name)

        block.write_error_check("!" + parser_idecl, handler=err_return)

        if len(to_cxx) > 0:
            block.append_blank_line()

            for line in to_cxx:
                block.write_code(line)

    def build_function_signature_parameter_list(self):
        return ", ".join([a.type.join_type_and_name(a.name) for a in self.args])

    def build_parameter_type_only_list(self):
        return ", ".join([a.type.decl() for a in self.args])

    def build_callmethod_args(self):
        if self.empty():
            return "NULL"

        fmt = self.get_fmt_specifier().replace('|', '')
        args = self.get_parameters_string()
        return '(char *) "%s", %s' % (fmt, args)


def test_empty():
    tk = TupleAndKeywords()

    print tk.get_keywords()
    print tk.build_parser_idecl()
    print tk.build_callmethod_args()

    assert len(tk.build_function_signature_parameter_list()) == 0


def test():
    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("int",), "FundamentalType"), "foo", 10))
    tk.add_parameter(Argument.Argument(Types.Type(("long int",), "FundamentalType"), "bar", 20))
    tk.add_parameter(Argument.Argument(Types.Type(("int",), "FundamentalType"), "mit", 30))

    print tk.get_fmt_specifier()
    print tk.get_keywords()
    print tk.build_parser_idecl()
    print tk.build_function_signature_parameter_list()
    print tk.build_callmethod_args()


def test_ptr():
    from Module import wxPythonNamer
    import CodeBlock

    tk = TupleAndKeywords()
    tk.add_parameter(Argument.Argument(Types.Type(("int", "*",), "FundamentalType"), "foo"))
    tk.add_parameter(Argument.Argument(Types.Type(("double", "&",), "FundamentalType"), "bar"))
    tk.add_parameter(Argument.Argument(Types.Type(("long unsigned int", "&", "const",), "FundamentalType"), "xyz"))
    tk.add_parameter(Argument.Argument(Types.Type(("X", "const", "&",), "FundamentalType"), "x"))
    tk.add_parameter(Argument.Argument(Types.Type(("Y", "*",), "FundamentalType"), "y"))
    tk.add_parameter(Argument.Argument(Types.Type(("Z",), "FundamentalType"), "z"))

    print tk.get_fmt_specifier()
    print tk.get_keywords()
    print tk.build_function_signature_parameter_list()

    namer = wxPythonNamer()

    print tk.build_parser_idecl(namer=namer)
    _print_empty_line()

    block = CodeBlock.CodeBlock()
    tk.write_args_parsing_code(namer=namer, block=block, err_return="return NULL;")
    print block.flush()


def _print_empty_line():
    print ""

if __name__ == "__main__":
    test_empty()

    _print_empty_line()
    test()

    _print_empty_line()
    test_ptr()