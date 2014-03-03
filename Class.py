import Methods
import Enum
import Module
import TupleAndKeywords
import Types
import Argument
import Code.Snippets
import CodeBlock
import pytypeobject
import HeaderJar
import Util


class Class:

    def __init__(self, root, node, module):
        self.root = root
        self.node = node
        self.block = CodeBlock.CodeBlock()
        self.namer = module.namer
        self.header_provider = module.header_provider
        self.owner_assigner = module.owner_assigner

        self.fwd_decl = set()

        self.only_private_ctors = False
        self.has_non_public_copy_ctors = False
        self.using_nonvirtual_protected = set()
        self.virtual_members = []

        self.bases = self._find_bases()

        self.enums = Enum.Enum()
        self.ctors = []
        self.methods = Methods.MethodJar()

        #---------------------------------------------------------------#

        self.name = node.attrib["name"]
        self.full_name = node.attrib["demangled"]

        self.header_jar = HeaderJar.HeaderJar()
        self.header_jar.add_headers(("Python", "_Common",))

        #---------------------------------------------------------------#

        self.enums.process(root, node.attrib["id"], self.namer)

        self._constructors()
        self._destructor()
        self._methods()

        #---------------------------------------------------------------#

        my_type = Types.Type((self.full_name,), node.tag)
        my_type.wrapt_name = self.get_wrapt_class_name()
        Types.Registry.add(my_type)

        Module.Module.add_class(self)

    def get_wrapt_class_name(self):
        wrapt = self.full_name
        if self._require_wrapper_class():
            wrapt = self.namer.wrapper_class(self.full_name)

        return wrapt

    def get_nester_class(self):
        context = self.root.find(".//*[@id='%s']" % self.node.attrib["context"])
        if context.tag in ("Class", "Struct"):
            return context.attrib["demangled"]
        else:
            return None

    def generate(self):
        self.block.write_code(self.header_provider.pch())

        self.header_jar.add_headers(self.header_provider.klass(self.full_name))
        for incl_hd in self.header_jar.headers:
            self.block.write_code(incl_hd)

        self.block.append_blank_line()

        #-------------------------------------------------------------------#

        if self._require_wrapper_class():
            self.block.write_code("class %s;\n" % self.get_wrapt_class_name())

        self.block.write_code(Code.Snippets.pyobj_decl % {
            "WRAPT": self.get_wrapt_class_name(),
            "PYTYPE_NAME": self.namer.pytype(self.full_name),
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
        })

        if self._require_wrapper_class():
            self._generate_wrapper_class()

        if not self._is_noncopyable():
            self._generate_exporter()

        self._generate_constructors()
        self._generate_destructor()
        self._generate_methods()
        self._generate_pytypeobject()
        self._generate_offset_base_ptr_func()
        self._generate_bases_register()
        self._generate_enums_register()
        self._generate_register()

    def _generate_register(self):
        template_args = {
            "REGISTER": self.namer.register(self.full_name),
            "PYTYPE": self.namer.pytype(self.full_name),
            "PYSIDE_SHORT": self.namer.to_python(self.name),
            "PYSIDE": self.namer.to_python(self.full_name),
        }

        nester = self.get_nester_class()
        if nester:
            pytype_nester = self.namer.pytype(nester)
            template_args["PYTYPE_NESTER"] = pytype_nester
            action = Code.Snippets.register_as_nested % template_args

            self.block.write_code("extern PyTypeObject %s;" % pytype_nester)
            self.block.append_blank_line()
        else:
            action = Code.Snippets.register_as_toplevel % template_args

        template_args["ACTION"] = action
        self.block.write_code(Code.Snippets.register_class % template_args)

    def _generate_exporter(self):
        self.block.write_code(Code.Snippets.exporter % {
            "CLASS": self.full_name,
            "WRAPT": self.get_wrapt_class_name(),
            "CLS_EMBBEDED": self.namer.to_python(self.full_name),
            "PYOBJ_STRUCT": self.namer.pyobj(self.full_name),
            "PYTYPE": self.namer.pytype(self.full_name),
        })

    def _find_bases(self):
        bases = []

        for base in self.node.findall("Base"):
            bnode = self.root.find(".//*[@id='%s']" % base.attrib["type"])
            bname = Util.full_name_of(bnode, self.root)
            bases.append(bname)

        return bases

    def _generate_offset_base_ptr_func(self):
        for base in self.bases:
            self.block.write_code("extern PyTypeObject %s;" % (
                self.namer.pytype(base)
            ))

        self.block.append_blank_line()

        self.block.write_code(Code.Snippets.offset_base_ptr % (
            self.namer.pytype(self.full_name),
        ))

        self.block.indent()

        for base in self.bases[1:]:
            self.block.write_code(Code.Snippets.offset_base_ptr_item % {
                "BASE_PYTYPE": self.namer.pytype(base),
                "BASE": base,
                "WRAPT": self.get_wrapt_class_name(),
            })

        self.block.unindent()
        self.block.write_code('}')
        self.block.append_blank_line()

    def _generate_bases_register(self):
        self.block.write_code(Code.Snippets.register_bases_sig % (
            self.namer.to_python(self.full_name)
        ))

        with CodeBlock.BracketThis(self.block):
            my_type = self.namer.pytype(self.full_name)
            if len(self.bases) > 0:
                self.block.write_code(my_type + ".tp_base = &%s;" % (
                    self.namer.pytype(self.bases[0]),
                ))

                if len(self.bases) > 1:
                    self.block.append_blank_line()
                    self.block.write_code(my_type + ".tp_bases = PyTuple_New(%d);" % (
                        len(self.bases)
                    ))

                    for index, base in enumerate(self.bases):
                        self.block.write_code(Code.Snippets.base_tuple_item % {
                            "BASE_TYPE": self.namer.pytype(base),
                            "INDEX": index,
                            "DERIVED_TYPE": my_type,
                        })
            else:
                self.block.append_blank_line()

    def _generate_enums_register(self):
        self.block.write_code(Code.Snippets.register_enums_sig % (
            self.namer.to_python(self.full_name)
        ))

        with CodeBlock.BracketThis(self.block):
            if len(self.enums.values) > 0:
                my_type = self.namer.pytype(self.full_name)
                action = Code.Snippets.register_class_enum_values % my_type

                self.enums.generate(self.block, action)
            else:
                self.block.append_blank_line()

    def _generate_pytypeobject(self):
        tp_obj = pytypeobject.PyTypeObject()
        tp_obj.slots["tp_name"] = "%s.%s" % (
            self.namer.package(), self.namer.fmt_path(self.full_name)
        )

        tp_obj.slots["tp_basicsize"] = "sizeof(%s)" % self.namer.pyobj(self.full_name)
        tp_obj.slots["typestruct"] = self.namer.pytype(self.full_name)
        tp_obj.slots["tp_dealloc"] = self.namer.destructor(self.full_name)

        if not self.only_private_ctors:
            tp_obj.slots["tp_flags"] = "Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE"

        if len(self.ctors) > 0:
            tp_obj.slots["tp_init"] = self.namer.constructor(self.full_name)

        if not self.methods.empty():
            tp_obj.slots["tp_methods"] = "_methods"

        tp_obj.generate(self.block)

    def _write_args_parsing_code(self, tk, err_return, pyside_debug_name=None):
        tk.write_args_parsing_code(namer=self.namer, block=self.block,
                                   err_return=err_return, enable_kw=True,
                                   args_tuple="args", kwargs_tuple="kwargs",
                                   pyside_debug_name=pyside_debug_name)

    def _write_overloads(self, func_name, signatures, err_return, actions,
                         finish_directly, pyside_debug_name=None):
        assert len(signatures) > 1
        assert len(signatures) == len(actions)

        func_name = func_name.upper()
        label_ok = "__%s_OK" % func_name

        self.block.write_code("PyObject *exceptions[] = { %s };" % (
            ("NULL, " * len(signatures))[:-2],
        ))

        self.block.append_blank_line()

        for index, (sig, action) in enumerate(zip(signatures, actions)):
            if index > 0:
                self.block.write_code((Code.Snippets.overloading_arg_parsing_label + ':') % {
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

            with CodeBlock.BracketThis(self.block, "___OVERLOAD___() "):
                self._write_args_parsing_code(sig, Code.Snippets.overloading_arg_parsing_err_handler % {
                    "FUNC_NAME": func_name,
                    "INDEX": index,
                    "ERR_RETURN": err_handler,
                }, pyside_debug_name=pyside_debug_name)

                self.block.write_code(action % sig.get_parameters_string())
                if not finish_directly:
                    self.block.write_code("goto %s;" % label_ok)

        if not finish_directly:
            self.block.write_code(label_ok + ':', temp_indent=0)

    def _constructors(self):
        private_ctor_count = 0

        for ctor in self.root.findall("Constructor[@context='%s']"
                                      % self.node.attrib["id"]):
            if ctor.attrib.get("artificial", None) == '1':
                continue

            access = ctor.attrib["access"]
            if access == "private":
                private_ctor_count += 1

            if ctor.attrib["demangled"] == "%s::%s(%s const&)" % ((self.name,) * 3):
                if access != "public":
                    self.has_non_public_copy_ctors = True

            if access == "public":
                self._constructor(ctor)

        if len(self.ctors) == 0:
            if private_ctor_count > 0:
                self.only_private_ctors = True
            else:
                self.ctors.append(TupleAndKeywords.TupleAndKeywords())

    def _constructor(self, ctor):
        print ctor.attrib["demangled"]

        tk = TupleAndKeywords.TupleAndKeywords()
        for argn in ctor.findall("Argument"):
            arg = Argument.Argument()
            arg.parse_xml(self.root, argn)
            tk.add_parameter(arg)

        self.ctors.append(tk)

    def _generate_constructors(self):
        name = self.namer.constructor(self.full_name)

        self.block.write_code(Code.Snippets.ctor_sig % {
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
            "CTOR_NAME": name,
        })

        with CodeBlock.BracketThis(self.block):
            if self.only_private_ctors:
                self.block.write_code(Code.Snippets.ctor_uninstanizable_error % {
                    "CLS_NAME": self.full_name,
                })

                return

            if self._is_abstract():
                self.block.write_code(Code.Snippets.ctor_chk_abstract % {
                    "PYTYPE_NAME": self.namer.pytype(self.full_name),
                    "CLS_NAME": self.full_name,
                })

            #-------------------------------------------------------------------#

            pyside_debug_name = "%s::%s" % (self.full_name, self.name,)
            action = "self->obj = new %s(%%s);" % self.get_wrapt_class_name()

            if len(self.ctors) == 1:
                args = self.ctors[0]

                self._write_args_parsing_code(args, "return -1;", pyside_debug_name=pyside_debug_name)
                self.block.write_code(action % args.get_parameters_string())
            else:
                self._write_overloads(name, self.ctors,
                                      err_return="return -1;",
                                      actions=(action,) * len(self.ctors),
                                      finish_directly=False,
                                      pyside_debug_name=pyside_debug_name)

            if self._require_wrapper_class():
                self.block.write_code("self->obj->self = (PyObject *) self;")

            self.block.write_code(Code.Snippets.ctor_actions_more % (
                self.owner_assigner.assign(self.full_name)
            ))

            self.block.write_code("return 0;")

    def _methods(self):
        for m in self.methods.process_class(self.root, self.node.attrib["id"]):
            if m.virtual:
                self.virtual_members.append(m)
            elif m.protected:
                self.using_nonvirtual_protected.add("using %s::%s;" % (
                    self.full_name, m.name
                ))

        if self.methods.require_type_info:
            self.header_jar.add_headers(("<typeinfo>",))

    def _generate_methods(self):
        self.methods.generate_methods(self.block, self.namer, self)

    def _require_wrapper_class(self):
        return len(self.virtual_members) > 0 or len(self.using_nonvirtual_protected) > 0

    def _is_abstract(self):
        for m in self.virtual_members:
            if m.pure_virtual:
                return True

        return False

    def _is_noncopyable(self):
        return self._is_abstract() or self.only_private_ctors or self.has_non_public_copy_ctors

    def collect_virtual_members(self):
        virtual_members = {
            vm.sig(): vm for vm in self.virtual_members
        }

        for base in self.bases:
            for vm in Module.get_class(base).collect_virtual_members():
                if vm.sig() not in virtual_members:
                    virtual_members[vm.sig()] = vm

        self.virtual_members = virtual_members.values()
        return self.virtual_members

    def _generate_wrapper_class(self):
        assert self._require_wrapper_class()

        wrapper_name = self.namer.wrapper_class(self.full_name)
        self.block.write_code("class %s : public %s" % (
            wrapper_name, self.full_name
        ))

        with CodeBlock.BracketThis(self.block, postscript=';'):
            self.block.write_code("public:", temp_indent=0)
            self.block.write_code("PyObject *self = nullptr;")
            self.block.append_blank_line()

            if len(self.using_nonvirtual_protected) > 0:
                for m in self.using_nonvirtual_protected:
                    self.block.write_code(m)

                self.block.append_blank_line()

            for ctor in self.ctors:
                self.block.write_code(wrapper_name + "(%s)" % (
                    ctor.build_function_signature_parameter_list()
                ))

                self.block.indent()
                self.block.write_code(": %s(%s)" % (
                    self.full_name, ctor.get_parameters_string()
                ))

                self.block.unindent()

                self.block.write_code("{}")
                self.block.append_blank_line()

            for m in self.virtual_members:
                pyside_debug_name = "%s %s" % (m.returns.decl(), m.raw_sig)

                self.block.write_code("virtual %s %s(%s)%s" % (
                    m.returns.decl(), m.name,
                    m.args.build_function_signature_parameter_list(),
                    " const" if m.raw_sig.endswith(" const") else "",
                ))

                template_args = {
                    "WRAPT": self.full_name,
                    "SIG": m.raw_sig,
                    "MNAME": m.name,
                    "ARGS_COUNT": m.args.size(),
                    "ARGS": m.args.get_parameters_string(),
                    "CM_ARGS": m.args.build_callmethod_args(),
                    "RET": m.returns.decl(),
                    "EXCEPTION": "CallPyMethodError",
                }

                with CodeBlock.BracketThis(self.block):
                    self.block.write_code(
                        Code.Snippets.virtual_method_wrapper_header(m.pure_virtual) % template_args
                    )

                    if m.returns.decl() == "void":
                        self.block.write_code(Code.Snippets.handle_return_void % pyside_debug_name)
                    else:
                        err_handler = "PyErr_Print();\n"
                        err_handler += Code.Snippets.throw_cxxexception % template_args

                        self.block.write_code(Code.Snippets.handle_return_non_void % err_handler)

                        tk = TupleAndKeywords.TupleAndKeywords()
                        tk.add_parameter(Argument.Argument(ctype=m.returns, name="retval"))

                        tk.write_args_parsing_code(namer=self.namer, block=self.block,
                                                   err_return=err_handler, enable_kw=False,
                                                   args_tuple="retval_tuple", kwargs_tuple="",
                                                   pyside_debug_name=pyside_debug_name)

                        self.block.write_code("return retval;")

    def _destructor(self):
        pass

    def _generate_destructor(self):
        self.block.write_code(Code.Snippets.dtor % {
            "DTOR_NAME": self.namer.destructor(self.full_name),
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
            "WRAPT": self.get_wrapt_class_name(),
        })

        self.block.append_blank_line()


def test():
    pass


if __name__ == "__main__":
    test()