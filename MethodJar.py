import copy
import Access
import Argument
import CodeBlock
import Session
import TupleAndKeywords
import Types
import Code.Snippets


class _InjectedMethod_TupleAndKeywords(TupleAndKeywords.TupleAndKeywords):
    def get_parameters_string(self):
        s = TupleAndKeywords.TupleAndKeywords.get_parameters_string(self)
        return "cxx_obj, " + s if s else "cxx_obj"


class Method:
    def __init__(self, root, node, free_function):
        self.name = node.attrib["name"]
        self.raw_sig = node.attrib["demangled"]

        self.free_function = free_function
        if not free_function:
            self.access = Access.access_type(node)
            self.virtual = node.attrib.get("virtual") == "1"
            self.final = node.attrib.get("final") == "1"
            self.pure_virtual = node.attrib.get("pure_virtual") == "1"
            self.static = node.attrib.get("static") == "1"

        self.args = TupleAndKeywords.TupleAndKeywords()
        for arg_node in node.findall("Argument"):
            self.args.add_parameter(Argument.from_xml(root, arg_node))

        self.returns = Types.get_type_by_id(node.attrib["returns"], root)

    def sig(self):
        return "%s(%s)%s" % (
            self.name, self.args.build_parameter_type_only_list(),
            " const" if self.raw_sig.endswith(" const") else "",
        )


class MethodJar:
    def __init__(self):
        self.methods = {}

    def size(self):
        return len(self.methods)

    def empty(self):
        return len(self.methods) == 0

    @staticmethod
    def _filter(root, mnode, allows_subclassing, blacklist):
        # always collect pure virtual functions
        if mnode.attrib.get("pure_virtual") == "1":
            return False

        if blacklist.method(mnode.attrib["demangled"]):
            Session.ignored_methods.add(mnode.attrib["demangled"])
            return True

        if MethodJar._filter_by_return_type(mnode, blacklist, root, Session.ignored_methods):
            return True

        maccess = Access.access_type(mnode)
        if not allows_subclassing and maccess != Access.PUBLIC:
            return True

        # private non-pure-virtuals will be handled later
        if maccess != Access.PRIVATE or mnode.attrib.get("virtual", None) == "1":
            return False

        # filter all the other
        return True

    def process_class(self, root, context_id, allows_subclassing, blacklist):
        assert isinstance(context_id, str)

        for mnode in root.findall("Method[@context='%s']" % context_id):
            if not MethodJar._filter(root, mnode, allows_subclassing, blacklist):
                self._method(mnode, root, False)

        self._strip_non_virtual_const_overloads()

        for overloads in self.methods.values():
            for m in overloads:
                yield m

    def process_free_functions(self, root, file_id, context_id, namespace, blacklist):
        methods_count0 = len(self.methods)

        xpath = "Function[@file='%s'][@context='%s']" % (file_id, context_id)
        for mnode in root.findall(xpath):
            if blacklist.free_function(mnode.attrib["demangled"]):
                Session.ignored_free_functions.add(mnode.attrib["demangled"])
                continue

            if self._filter_by_return_type(mnode, blacklist, root, Session.ignored_free_functions):
                continue

            m = self._method(mnode, root, True)
            m.namespace = namespace

        return len(self.methods) - methods_count0

    @staticmethod
    def _filter_by_return_type(mnode, blacklist, root, logset):
        ret = Types.get_type_by_id(mnode.attrib["returns"], root)

        if blacklist.return_type(ret):
            logset.add("[%s]" % ret.decl() + mnode.attrib["demangled"])
            return True

        return False

    def _method(self, mnode, root, free_function):
        print(mnode.attrib["demangled"])

        m = Method(root, mnode, free_function)
        overloads = self.methods.setdefault(m.name, [])

        for o in overloads:
            if o.raw_sig == m.raw_sig:
                return m

        overloads.append(m)
        return m

    def remove_private_non_pure_virtuals(self, private_non_pure_virtuals):
        for vm in private_non_pure_virtuals:
            overloads = self.methods[vm.name]

            if len(overloads) == 1:
                del self.methods[vm.name]
            else:
                overloads.remove(vm)

    def collect_function_pointer_defs(self, fptr_mgr):
        for overloads in self.methods.values():
            for m in overloads:
                for arg in m.args.args:
                    fptr_mgr.try_add(arg.type)

                fptr_mgr.try_add(m.returns)

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
                    if self._search_non_const_overload(overloads, m.raw_sig):
                        to_strip.add(m)

            self.methods[mname] = list(set(overloads) - to_strip)

    @staticmethod
    def _normalize_method_name(mname, namer):
        return namer.normalize_template(mname) if '<' in mname else mname

    def generate_methods(self, block, namer, cls):
        assert isinstance(block, CodeBlock.CodeBlock)

        for mname in sorted(self.methods.keys()):
            overloads = sorted(self.methods[mname], lambda x, y: cmp(x.raw_sig, y.raw_sig))

            if not _validate_overloads(overloads):
                ns = cls.full_name + "::" if cls else ""
                print("`%s%s`: _validate_overloads() failed." % (ns, mname))
                assert False

            signatures = []
            actions = []

            for m in overloads:
                is_real_class_member = cls and not m.free_function

                if cls and m.free_function:
                    args_tk = copy.copy(m.args)
                    args_tk.__class__ = _InjectedMethod_TupleAndKeywords
                    args_tk.args = args_tk.args[1:]

                    signatures.append(args_tk)
                else:
                    signatures.append(m.args)

                if is_real_class_member:
                    invoker = "cxx_obj->"
                    if m.static:
                        invoker = cls.get_wrapt_class_name() + "::"
                else:
                    invoker = "" if not m.namespace else m.namespace + "::"

                if m.returns.decl() != "void":
                    if m.returns.category() == Types.CLASS:
                        fmt = "%s(%s%s(%%s));\n%s\n\n"
                    else:
                        fmt = "%s = %s%s(%%s);\n%s\n\n"

                    action = "PBPP_BEGIN_ALLOW_THREADS\n"
                    action += fmt % (
                        m.returns.join_type_and_name("retval"),
                        invoker,
                        m.name,  # ATTENTION!
                        "PBPP_END_ALLOW_THREADS"
                    )

                    if m.returns.is_ptr():
                        action += Code.Snippets.ensure_not_null + '\n'

                    if m.returns.is_pyobject_ptr():
                        action += "return retval;"
                    else:
                        idecl = m.returns.get_build_value_idecl("retval", namer=namer)
                        action += idecl + "\nreturn (PyObject *) py_retval;"
                else:
                    action = Code.Snippets.invoke_fx_returning_void % (invoker, m.name)

                actions.append(action)


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
                "PYOBJ_NAME": "" if not cls else namer.pyobj(cls.full_name),
                "NAME": self._normalize_method_name(mname, namer),
            })


            with CodeBlock.BracketThis(block):
                if cls:
                    pyside = cls.full_name + "::" + mname
                else:
                    pyside = mname

                if not cls or (hasattr(overloads[0], "static") and overloads[0].static):
                    pass
                else:
                    block.write_code(Code.Snippets.TestSubclassAndOffset % {
                        "CLS_NAME": cls.full_name,
                        "MY_PYTYPE": namer.pytype(cls.full_name),
                        "WRAPT": cls.get_wrapt_class_name(),
                    })

                    block.append_blank_line()

                if len(overloads) == 1:
                    if not signatures[0].empty():
                        signatures[0].write_args_parsing_code(
                            block, namer, True, "return nullptr;", pyside
                        )

                    block.write_code(actions[0] % signatures[0].get_parameters_string())
                else:
                    _write_overloads(block=block,
                                     namer=namer, func_name=mname,
                                     signatures=signatures,
                                     err_return="return nullptr;",
                                     actions=actions,
                                     finish_directly=True,
                                     pyside_debug_name=pyside)

        if not cls:
            self.generate_method_table(block, namer, cls)

    def generate_method_table(self, block, namer, cls):
        block.write_code(Code.Snippets.method_table_begin)
        block.indent()

        for mname in sorted(self.methods.keys()):
            overloads = self.methods[mname]
            m0 = overloads[0]

            flags = ""
            if len(overloads) == 1 and m0.args.empty():
                flags += "METH_NOARGS"
            else:
                flags += "METH_KEYWORDS | METH_VARARGS"

            if not m0.free_function and m0.static:
                flags += " | METH_STATIC"

            normalized_name = self._normalize_method_name(mname, namer)
            block.write_code('{ (char *) "%s", (PyCFunction) %s, %s, nullptr },' % (
                namer.to_python(mname),
                "__M::" + normalized_name if cls else "__" + normalized_name,
                flags,
            ))

        block.unindent()
        block.write_code(Code.Snippets.method_table_end)


def _write_overloads(block, namer, func_name, signatures, err_return, actions,
                     finish_directly, pyside_debug_name=None):
    assert len(signatures) > 1
    assert len(signatures) == len(actions)

    func_name = func_name.upper()
    label_ok = "__%s_OK" % func_name

    block.write_code(Code.Snippets.overloading_exception_cache % len(signatures))

    for index, (sig, action) in enumerate(zip(signatures, actions)):
        if index > 0:
            block.write_code((Code.Snippets.overloading_label + ':') % {
                "FUNC_NAME": func_name,
                "INDEX": index,
            }, temp_indent=0)

        if index < len(signatures) - 1:
            err_handler = "goto " + Code.Snippets.overloading_label % {
                "FUNC_NAME": func_name,
                "INDEX": index + 1,
            } + ';'
        else:
            err_handler = (Code.Snippets.overloading_restore_exceptions %
                           len(signatures)) + err_return

        with CodeBlock.BracketThis(block, "___OVERLOAD___() "):
            r = Code.Snippets.overloading_cache_exception % index + err_handler
            sig.write_args_parsing_code(block, namer, True, r, pyside_debug_name)

            block.write_code(action % sig.get_parameters_string())
            if not finish_directly:
                block.write_code("goto %s;" % label_ok)

    if not finish_directly:
        block.write_code(label_ok + ':', temp_indent=0)
    else:
        block.lines.pop()  # Remove the last empty line


def _validate_overloads(overloads):
    num_static_overloads = 0
    for m in overloads:
        if hasattr(m, "static") and m.static:
            num_static_overloads += 1

    return num_static_overloads == 0 or num_static_overloads == len(overloads)
