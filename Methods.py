import Argument
import CodeBlock
import TupleAndKeywords
import Types
import Code.Snippets


class Method:

    def __init__(self, root, node, free_function):
        self.free_function = free_function
        self.name = node.attrib["name"]
        self.raw_sig = node.attrib["demangled"]

        if not free_function:
            self.protected = node.attrib.get("access", None) == "protected"
            self.virtual = node.attrib.get("virtual", None) == "1"
            self.pure_virtual = node.attrib.get("pure_virtual", None) == "1"
            self.static = node.attrib.get("static", None) == "1"

        self.args = TupleAndKeywords.TupleAndKeywords()
        for arg_node in node.findall("Argument"):
            self.args.add_parameter(Argument.from_xml(root, arg_node))

        self.returns = Types.get_type_from_id(node.attrib["returns"], root)

    def sig(self):
        return "%s(%s)%s" % (
            self.name, self.args.build_parameter_type_only_list(),
            " const" if self.raw_sig.endswith(" const") else "",
        )


class MethodJar:

    def __init__(self):
        self.methods = {}
        self.require_type_info = False

    def size(self):
        return len(self.methods)

    def empty(self):
        return len(self.methods) == 0

    def process_class(self, root, context_id):
        assert isinstance(context_id, str)

        for mnode in root.findall("Method[@context='%s']" % context_id):
            if (not mnode.get("access", None) == "private" or
                    mnode.get("virtual", None) == "1"):

                self._method(mnode, root, False)

        self._strip_non_virtual_const_overloads()

        for overloads in self.methods.values():
            for m in overloads:
                yield m

    def process_free_functions(self, root, context_id, namespace):
        assert isinstance(context_id, str)

        for mnode in root.findall("Function[@context='%s']" % context_id):
            m = self._method(mnode, root, True)
            m.namespace = namespace

    def _method(self, mnode, root, free_function):
        print mnode.attrib["demangled"]

        m = Method(root, mnode, free_function)
        self.methods.setdefault(m.name, []).append(m)

        if m.returns.is_ptr_or_ref() and not m.returns.is_trivial():
            self.require_type_info = True

        return m

    @staticmethod
    def _search_non_const_overload(overloads, sig):
        sig_no_const = sig[:-6]

        for m in overloads:
            if (not m.virtual) and m.raw_sig == sig_no_const:
                return m

        return None

    def _strip_non_virtual_const_overloads(self):
        for mname in self.methods:
            overloads = self.methods[mname]
            if len(overloads) == 1:
                continue

            to_strip = set()
            for m in overloads:
                if (not m.virtual) and m.raw_sig.endswith(" const"):
                    print "===>", m.raw_sig
                    if self._search_non_const_overload(overloads, m.raw_sig):
                        to_strip.add(m)

            self.methods[mname] = list(set(overloads) - to_strip)

    def generate_methods(self, block, namer, cls):
        assert isinstance(block, CodeBlock.CodeBlock)

        for mname in self.methods:
            overloads = self.methods[mname]
            assert _validate_overloads(overloads)

            signatures = []
            actions = []

            for m in overloads:
                signatures.append(m.args)

                if cls:
                    invoker = "obj->"
                    if m.static:
                        invoker = cls.full_name + "::"
                else:
                    invoker = "" if not m.namespace else m.namespace + "::"

                if m.returns.decl() != "void":
                    if m.returns.category() == Types.CLASS:
                        fmt = "%s(%s%s(%%s));\n"
                    else:
                        fmt = "%s = %s%s(%%s);\n"

                    action = fmt % (
                        m.returns.join_type_and_name("retval"),
                        invoker, mname,
                    )

                    if m.returns.is_ptr():
                        action += Code.Snippets.ensure_not_null

                    idecl = m.returns.get_build_value_idecl("retval", namer)
                    action += idecl + "\nreturn (PyObject *) py_retval;"
                else:
                    action = "%s%s(%%s);\n" % (invoker, mname)
                    action += "Py_RETURN_NONE;"

                actions.append(action)

            #---------------------------------------------------------------#

            if len(overloads) == 1 and overloads[0].args.empty():
                if cls:
                    method_sig = Code.Snippets.method_sig_no_arg
                else:
                    method_sig = Code.Snippets.ff_sig_no_arg
            else:
                if cls:
                    method_sig = Code.Snippets.method_sig
                else:
                    method_sig = Code.Snippets.ff_sig

            block.write_code(method_sig % {
                "NAME": mname,
                "PYOBJ_NAME": "" if not cls else namer.pyobj(cls.full_name),
            })

            with CodeBlock.BracketThis(block):
                if cls:
                    pyside = cls.full_name + "::" + mname
                else:
                    pyside = mname

                if cls and not m.static:
                    block.write_code(Code.Snippets.TestSubclassAndOffset % {
                        "MY_PYTYPE": namer.pytype(cls.full_name),
                        "WRAPT": cls.get_wrapt_class_name(),
                    })

                if len(overloads) == 1:
                    if not m.args.empty():
                        m.args.write_args_parsing_code(
                            namer=namer, block=block,
                            err_return="return NULL;",
                            pyside_debug_name=pyside
                        )

                    block.write_code(actions[0] % m.args.get_parameters_string())
                else:
                    _write_overloads(block=block,
                                     namer=namer, func_name=mname,
                                     signatures=signatures,
                                     err_return="return NULL;",
                                     actions=actions,
                                     finish_directly=True,
                                     pyside_debug_name=pyside)

        self._generate_method_table(block)

    def _generate_method_table(self, block):
        block.write_code(Code.Snippets.method_table_begin)
        block.indent()

        for mname in self.methods:
            overloads = self.methods[mname]
            m0 = overloads[0]

            flags = ""
            if len(overloads) == 1 and m0.args.empty():
                flags += "METH_NOARGS"
            else:
                flags += "METH_KEYWORDS | METH_VARARGS"

            if not m0.free_function and m0.static:
                flags += " | METH_STATIC"

            block.write_code('{ (char *) "%s", (PyCFunction) %s, %s, NULL },' % (
                mname, mname if not m0.free_function else "__" + mname, flags,
            ))

        block.unindent()
        block.write_code(Code.Snippets.method_table_end)


def _write_overloads(block, namer, func_name, signatures, err_return, actions,
                     finish_directly, pyside_debug_name=None):
    assert len(signatures) > 1
    assert len(signatures) == len(actions)

    func_name = func_name.upper()
    label_ok = "__%s_OK" % func_name

    block.write_code("PyObject *exceptions[] = { %s };" % (
        ("NULL, " * len(signatures))[:-2],
    ))

    block.append_blank_line()

    for index, (sig, action) in enumerate(zip(signatures, actions)):
        if index > 0:
            block.write_code((Code.Snippets.overloading_arg_parsing_label + ':') % {
                "FUNC_NAME": func_name,
                "INDEX": index,
            }, temp_indent=0)

        if index < len(signatures) - 1:
            err_handler = "goto " + Code.Snippets.overloading_arg_parsing_label % {
                "FUNC_NAME": func_name,
                "INDEX": index + 1,
            } + ';'
        else:
            err_handler = "PyObject *error_list = PyList_New(%d);\n" % len(signatures)
            for i in range(len(signatures)):
                err_handler += Code.Snippets.overloading_arg_parsing_err_return % {
                    "INDEX": i,
                }

            err_handler += Code.Snippets.overloading_arg_parsing_set_exception
            err_handler += err_return

        with CodeBlock.BracketThis(block, "___OVERLOAD___() "):
            sig.write_args_parsing_code(
                namer=namer, block=block,
                err_return=Code.Snippets.overloading_arg_parsing_err_handler % {
                    "FUNC_NAME": func_name,
                    "INDEX": index,
                    "ERR_RETURN": err_handler,
                },
                pyside_debug_name=pyside_debug_name)

            block.write_code(action % sig.get_parameters_string())
            if not finish_directly:
                block.write_code("goto %s;" % label_ok)

    if not finish_directly:
        block.write_code(label_ok + ':', temp_indent=0)


def _validate_overloads(overloads):
    num_static_overloads = 0
    for m in overloads:
        if hasattr(m, "static") and m.static:
            num_static_overloads += 1

    return num_static_overloads == 0 or num_static_overloads == len(overloads)