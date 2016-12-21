import Access
import Argument
import Code.Snippets
import CodeBlock
import Enum
import Fptr
import HeaderJar
import MethodJar
import Registry
import Session
import TupleAndKeywords
import Types
import pytypeobject


# Object lifetime management policies
LT_PYTHON = 0
LT_CXX = 1
LT_BORROWED = 2


class Class:
    class DummyDef:
        def __init__(self, **kwargs):
            self.name = kwargs["name"]
            self.full_name = kwargs["full_name"]
            self.enum_class = kwargs.get("enum_class", False)
            self.is_struct = kwargs.get("is_struct", False)
            self.namespace = kwargs.get("namespace", "")
            self.nester = kwargs.get("nester", "")
            self.header = kwargs.get("header", None)

    def __init__(self, root, node, module, dummy_def=None):
        assert node is not None or dummy_def is not None

        # Only effective while processing
        self.root = root
        self.node = node

        self.namer = module.namer
        self.header_provider = module.header_provider
        self.flags_assigner = module.flags_assigner
        self.blacklist = module.blacklist

        self.all_bases = None
        self.master_bases = None

        self.final = False

        # No accessible canonical ctors -> disallow subclassing
        # `canonical ctor` refers to a ctor that is not a copy ctor
        self.no_accessible_canonical_ctors = False

        # If true, requires a wrapper class
        # We only save constructors' params, so we can't determine
        # whether the class has any protected constructor when
        # generating the output
        self.has_protected_ctor = False

        # Instantiatable (new-able) != delete-able
        self.dtor_access_type = Access.PUBLIC

        self.copy_ctor_access_type = Access.PUBLIC
        self.base_private_copy_ctor_checked = False
        self.arch_has_private_copy_ctor = False

        self.protected_nonvirtual_members = set()
        self.public_nonvirtual_methods = []
        self.virtual_members = []
        self.base_vm_collected = False

        self.enums = Enum.Enum()

        self.ctors = []
        self.methods = MethodJar.MethodJar()
        self.fields = []
        self.fptrs = Fptr.FptrManager()

        self.header_jar = HeaderJar.HeaderJar()
        self.header_jar.add_headers(("_Python.hxx", "_Common.hxx",))
        if module.header_decl:
            self.header_jar.add_headers((module.header_decl,))

        # These properties only accessed by the Module class
        self.modified = True
        self.m = None

        # For temporary use only, avoid passing it everywhere
        self.block = CodeBlock.CodeBlock()

        if dummy_def is not None:
            self.name = dummy_def.name
            self.full_name = dummy_def.full_name

            self.enum_class = dummy_def.enum_class

            self.nester = dummy_def.nester
            self.direct_bases = []

            # TODO: namespace alias
            if (not dummy_def.namespace and
                    not dummy_def.nester and
                    not dummy_def.enum_class):
                assert self.name == self.full_name

                self.header_jar.add_global("%s %s;" % (
                    "struct" if dummy_def.is_struct else "class",
                     self.name
                ))

            # Instantiating, destroying, copying or inheriting
            # a dummy class (object) is not allowed

            self.final = True

            self.no_accessible_canonical_ctors = True
            self.dtor_access_type = Access.PRIVATE

            self.copy_ctor_access_type = Access.PRIVATE
            self.base_private_copy_ctor_checked = True
            self.arch_has_private_copy_ctor = True
        else:
            Session.begin(self.header_jar)

            self.name = node.attrib["name"]
            self.full_name = node.attrib["demangled"]

            self.enum_class = False

            self.nester = self._get_nester_class()
            self.direct_bases = self._collect_direct_bases()

            self.final = node.attrib.get("final") == "1"

            self._constructors()
            self._destructor()  # Check dtor's access type

            self._methods()
            self._enums(module)
            self._fields()

            Session.end()

    @staticmethod
    def instantiate_scoped_enum(se, module, nester):
        assert isinstance(se, Enum.ScopedEnum)
        assert nester is None or isinstance(nester, Class)

        dummy_def = Class.DummyDef(
            name=se.name,
            full_name=se.full_name,
            enum_class=True,
            nester=nester.full_name if nester else None
        )

        enum_class = Class(None, None, module, dummy_def)
        enum_class.enums.values = se.values

        return enum_class

    def prepare_for_serializing(self):
        self.root = None
        self.node = None

    def set_header(self, header):
        self.header_jar.add_headers((header,))

    def get_wrapt_class_name(self):
        if self.enum_class:
            return "pbpp::ScopedEnumDummy"

        wrapt = self.full_name
        if self._require_wrapper_class():
            wrapt = self.namer.wrapper_class(self.full_name)

        return wrapt

    def _get_nester_class(self):
        context = self.root.find(".//*[@id='%s']" % self.node.attrib["context"])
        if context.tag in ("Class", "Struct"):
            return context.attrib["demangled"]
        else:
            return None

    def _get_lifetime_policy(self):
        policy = self.flags_assigner.assign(self.full_name)
        if policy == "pbpp::LifeTime::CXX":
            return LT_CXX
        elif policy == "pbpp::LifeTime::BORROWED":
            return LT_BORROWED
        else:
            return LT_PYTHON

    def inject_as_method(self, overloads, new_name, headers):
        # Attention -- DO NOT modify overloads in place
        new = overloads + self.methods.methods.get(new_name, [])
        self.methods.methods[new_name] = new

        if headers:
            self.header_jar.add_headers(headers)

    def generate(self):
        Session.begin(self.header_jar)

        if self._require_wrapper_class():
            self.block.write_code("class %s;" % self.get_wrapt_class_name())
            self.block.append_blank_line()

        self.block.write_code(Code.Snippets.pyobj_decl % {
            "WRAPT": self.get_wrapt_class_name(),
            "PYTYPE_NAME": self.namer.pytype(self.full_name),
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
        })

        if not self.fptrs.empty():
            self.fptrs.generate(self.block)
            self.block.append_blank_line()

        if self._require_wrapper_class():
            self._generate_wrapper_class()

        if not self.enum_class:
            self._generate_borrower()

        if not self._is_noncopyable():
            self._generate_copyer()

        self.block.write_code("namespace {")

        if self.allows_subclassing() or self.enum_class:
            if not self.enum_class:
                method_wrapper_base = self.full_name
            else:
                method_wrapper_base = self.nester or "pbpp::ScopedEnumDummy"

            self.block.write_code("struct __M : public %s {" % method_wrapper_base)
        else:
            self.block.write_code("struct __M {")

        self.block.append_blank_line()

        self._generate_constructors()
        self._generate_destructor()
        self._generate_methods()
        self._generate_enums()
        self._generate_fields()

        self.block.write_code("}; // struct __M")
        self.block.write_code("}  // namespace")
        self.block.append_blank_line()

        self._generate_method_table()
        self._generate_getset_table()

        self._generate_pytypeobject()
        self._generate_offset_base_ptr_func()
        self._generate_bases_register()
        self._generate_register()

        Session.end()

        # TODO: Why can't do this in ctor?
        self.header_jar.add_headers(self.header_provider.klass(self.full_name))
        if self._require_wrapper_class():
            self.header_jar.add_headers(("<typeinfo>",))

        memblock = CodeBlock.CodeBlock()

        memblock.write_code(self.header_provider.pch())
        memblock.write_code(self.header_jar.concat_sorted())
        memblock.append_blank_line()

        # TODO: a dirty trick
        self.block.lines = memblock.lines + self.block.lines

        self.modified = False

    def _enums(self, module):
        if self.enums.process(self.root, module.current_file_id(),
                              self.node.attrib["id"],
                              self.allows_subclassing(),
                              self.namer):
            for se in self.enums.scoped_enums.values():
                cls = Class.instantiate_scoped_enum(se, module, self)
                module.register_class(cls)

    def _fields(self):
        for fnode in self.root.findall("Field[@context='%s']" % self.node.attrib["id"]):
            access_type = Access.access_type(fnode)

            if access_type == Access.PRIVATE:
                continue

            if access_type == Access.PROTECTED and not self.allows_subclassing():
                continue

            name = fnode.attrib["name"]

            # union
            if not name:
                continue

            if self.blacklist.field(self.full_name, name):
                full_name = self.full_name + "::" + name
                Session.ignored_fields.add(full_name)
                continue

            t = Types.get_type_by_id(fnode.attrib["type"], self.root)
            f = Argument.Argument(t, name)
            self.fields.append(f)

            if access_type == Access.PROTECTED:
                self.protected_nonvirtual_members.add("using %s::%s;" % (
                    self.full_name, f.raw_name
                ))

    def _generate_getter(self, f):
        self.block.write_code(Code.Snippets.field_getter_sig % (
            self.namer.getter(f.raw_name), self.namer.pyobj(self.full_name)
        ))

        with CodeBlock.BracketThis(self.block):
            self.block.write_code(Code.Snippets.TestSubclassAndOffset % {
                "MY_PYTYPE": self.namer.pytype(self.full_name),
                "WRAPT": self.get_wrapt_class_name(),
            })

            self.block.append_blank_line()

            self.block.write_code(f.type.get_build_value_idecl(
                "cxx_obj->" + f.raw_name, namer=self.namer
            ))

            self.block.append_blank_line()
            self.block.write_code("return py_%s;" % f.raw_name)

    def _generate_setter(self, f):
        assert not f.type.is_ref()

        self.block.write_code(Code.Snippets.field_setter_sig % (
            self.namer.setter(f.raw_name), self.namer.pyobj(self.full_name)
        ))

        with CodeBlock.BracketThis(self.block):
            self.block.write_code(Code.Snippets.TestSubclassAndOffset % {
                "MY_PYTYPE": self.namer.pytype(self.full_name),
                "WRAPT": self.get_wrapt_class_name(),
            })

            self.block.append_blank_line()
            self.block.write_code(f.type.get_extractor_code(
                f.name, "py_value", "return -1;", self.namer
            ))

            self.block.append_blank_line()

            if f.type.is_class_value():
                self.block.write_lines((
                    "PBPP_BEGIN_ALLOW_THREADS",
                    "cxx_obj->%s = %s;" % (f.raw_name, f.name),
                    "PBPP_END_ALLOW_THREADS",
                    "",
                ))
            else:
                self.block.write_code("cxx_obj->%s = %s;" % (f.raw_name, f.name))

            self.block.write_code("return 0;")

    def _generate_fields(self):
        if len(self.fields) == 0:
            return

        for f in self.fields:
            self._generate_getter(f)
            self._generate_setter(f)

    def _generate_getset_table(self):
        self.block.write_code(Code.Snippets.field_table_begin)

        for f in self.fields:
            self.block.write_code(Code.Snippets.field_table_entry % {
                "GETTER": "__M::" + self.namer.getter(f.raw_name),
                "SETTER": "__M::" + self.namer.setter(f.raw_name),
                "NAME": f.raw_name,
            })

        self.block.write_code(Code.Snippets.field_table_end)

    def _generate_register(self):
        template_args = {
            "REGISTER": self.namer.register(self.full_name),
            "PYTYPE": self.namer.pytype(self.full_name),
            "PYSIDE_SHORT": self.namer.to_python(self.name),
            "PYSIDE": self.namer.to_python(self.full_name),
        }

        if self.nester:
            pytype_nester = self.namer.pytype(self.nester)
            template_args["PYTYPE_NESTER"] = pytype_nester
            action = Code.Snippets.register_as_nested % template_args

            self.block.write_code("extern PyTypeObject %s;" % pytype_nester)
            self.block.append_blank_line()
        else:
            action = Code.Snippets.register_as_toplevel % template_args

        template_args["ACTION"] = action
        self.block.write_code(Code.Snippets.register_class % template_args)

    def _generate_borrower(self):
        interfaces = Types.PythonAwareClassRegistry.find(self.full_name)
        if interfaces:
            quick_borrow = Code.Snippets.borrow_from_python_aware_class % {
                "PYOBJ_STRUCT": self.namer.pyobj(self.full_name),
                "SELF_GETTER": interfaces.self_getter,
            }
        else:
            quick_borrow = ""

        template_args = {
            "CLASS": self.full_name,
            "WRAPT": self.get_wrapt_class_name(),
            "BORROWER": self.namer.borrower(self.full_name),
            "PYOBJ_STRUCT": self.namer.pyobj(self.full_name),
            "PYTYPE": self.namer.pytype(self.full_name),
            "QUICK_BORROW": quick_borrow,
        }

        if self._require_wrapper_class():
            self.block.write_code(Code.Snippets.borrower2 % template_args)
        else:
            self.block.write_code(Code.Snippets.borrower % template_args)

    def _generate_copyer(self):
        assert not self._is_noncopyable()

        init_helper_self = ""
        if self._require_wrapper_class():
            init_helper_self = Code.Snippets.init_helper_self

        self.block.write_code(Code.Snippets.copyer % {
            "CLASS": self.full_name,
            "WRAPT": self.get_wrapt_class_name(),
            "COPYER": self.namer.copyer(self.full_name),
            "INIT_HELPER_SELF": init_helper_self,
            "PYOBJ_STRUCT": self.namer.pyobj(self.full_name),
            "PYTYPE": self.namer.pytype(self.full_name),
        })

    def _collect_direct_bases(self):
        bases = []

        for base in self.node.findall("Base"):
            bnode = self.root.find(".//*[@id='%s']" % base.attrib["type"])
            bname = bnode.attrib["demangled"]

            if not self.blacklist.base(bname):
                bases.append(bname)
            else:
                Session.ignored_bases.add(bname)

        return bases

    def collect_all_bases(self):
        if self.all_bases is None:
            self.all_bases = set(self.direct_bases)
            self.master_bases = set()
            if len(self.direct_bases) > 0:
                self.master_bases.add(self.direct_bases[0])

            for index, base_name in enumerate(self.direct_bases):
                base = Registry.get_class(base_name)
                base.collect_all_bases()

                self.all_bases |= base.all_bases
                if index == 0:
                    self.master_bases |= base.master_bases

    def _generate_offset_base_ptr_func(self):
        secondly_bases = self.all_bases - self.master_bases

        for base in set(self.direct_bases) | secondly_bases:
            self.block.write_code("extern PyTypeObject %s;" % (
                self.namer.pytype(base)
            ))

        if len(self.direct_bases) > 0:
            self.block.append_blank_line()

        if len(secondly_bases) == 0:
            self.block.write_code(Code.Snippets.offset_base_ptr_simple)
        else:
            self.block.write_code(Code.Snippets.offset_base_ptr_header % (
                self.namer.pytype(self.full_name),
            ))

            self.block.indent()

            for base in secondly_bases:
                self.block.write_code(Code.Snippets.offset_base_ptr_item % {
                    "BASE_PYTYPE": self.namer.pytype(base),
                    "BASE": base,
                    "WRAPT": self.get_wrapt_class_name(),
                })

            self.block.append_blank_line()
            self.block.write_code("return cxx_obj;")

            self.block.unindent()
            self.block.write_code('}')

        self.block.append_blank_line()

    def _generate_bases_register(self):
        self.block.write_code(Code.Snippets.register_bases_sig)

        if len(self.direct_bases) == 0:
            self.block.lines[-1] += " {}\n"
            return

        with CodeBlock.BracketThis(self.block):
            my_type = self.namer.pytype(self.full_name)

            self.block.write_code(my_type + ".tp_base = &%s;" % (
                self.namer.pytype(self.direct_bases[0]),
            ))

            if len(self.direct_bases) > 1:
                self.block.append_blank_line()
                self.block.write_code(my_type + ".tp_bases = PyTuple_New(%d);" % (
                    len(self.direct_bases)
                ))

                for index, base in enumerate(self.direct_bases):
                    self.block.write_code(Code.Snippets.base_tuple_item % {
                        "BASE_TYPE": self.namer.pytype(base),
                        "INDEX": index,
                        "DERIVED_TYPE": my_type,
                    })

    def _generate_enums(self):
        self.block.write_code(Code.Snippets.register_enums_sig)

        if len(self.enums.values) > 0:
            with CodeBlock.BracketThis(self.block):
                my_type = self.namer.pytype(self.full_name)
                action = Code.Snippets.register_class_enum_values % my_type

                self.enums.generate(self.block, action)
        else:
            self.block.lines[-1] += " {}\n"

    def _generate_pytypeobject(self):
        tp_obj = pytypeobject.PyTypeObject()
        tp_obj.slots["tp_name"] = "%s.%s" % (
            self.namer.package(), self.namer.fmt_path(self.full_name)
        )

        tp_obj.slots["tp_basicsize"] = "sizeof(%s)" % self.namer.pyobj(self.full_name)
        tp_obj.slots["typestruct"] = self.namer.pytype(self.full_name)

        # Always define an init function
        # For uninstantiatable classes, tell the caller
        ctor = "__M::" + self.namer.constructor(self.full_name)
        tp_obj.slots["tp_init"] = ctor

        # Always define a dealloc function
        dtor = "__M::" + self.namer.destructor(self.full_name)
        tp_obj.slots["tp_dealloc"] = dtor

        if self.allows_subclassing():
            tp_obj.slots["tp_flags"] = "Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE"

        if not self.methods.empty():
            tp_obj.slots["tp_methods"] = "__methods"

        if len(self.fields) > 0:
            tp_obj.slots["tp_getset"] = "__getsets"

        tp_obj.generate(self.block)

    def _write_args_parsing_code(self, tk, err_return, pyside_debug_name):
        tk.write_args_parsing_code(self.block, self.namer, True, err_return, pyside_debug_name)

    def _write_overloads(self, func_name, signatures, err_return, actions,
                         finish_directly, pyside_debug_name=None):
        assert len(signatures) > 1
        assert len(signatures) == len(actions)

        func_name = func_name.upper()
        label_ok = "__%s_OK" % func_name

        self.block.write_code(Code.Snippets.overloading_exception_cache % len(signatures))

        for index, (sig, action) in enumerate(zip(signatures, actions)):
            if index > 0:
                self.block.write_code((Code.Snippets.overloading_label + ':') % {
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

            with CodeBlock.BracketThis(self.block, "___OVERLOAD___() "):
                r = Code.Snippets.overloading_cache_exception + err_handler
                self._write_args_parsing_code(sig, r, pyside_debug_name)

                self.block.write_code(action % sig.get_parameters_string())
                if not finish_directly:
                    self.block.write_code("goto %s;" % label_ok)

        if not finish_directly:
            self.block.write_code(label_ok + ':', temp_indent=0)

    def _constructors(self):
        has_private_ctor = False

        for ctor in self.root.findall("Constructor[@context='%s']" % self.node.attrib["id"]):
            if ctor.attrib.get("artificial", None) == '1':
                continue

            access = Access.access_type(ctor)
            if access == Access.PRIVATE:
                has_private_ctor = True

            # Artificial copy constructors are public
            args_sig = "(const %s &)" % self.full_name
            if ctor.attrib["demangled"].endswith(args_sig):
                self.copy_ctor_access_type = access

            if access != Access.PRIVATE:
                if not self.blacklist.method(ctor.attrib["demangled"]):
                    self._constructor(ctor)

                    if access == Access.PROTECTED:
                        self.has_protected_ctor = True
                else:
                    Session.ignored_methods.add(ctor.attrib["demangled"])

        if len(self.ctors) == 0:
            if has_private_ctor:
                self.no_accessible_canonical_ctors = True
            else:
                # Define a default ctor for easy generating
                self.ctors.append(TupleAndKeywords.TupleAndKeywords())

    def _constructor(self, ctor):
        print(ctor.attrib["demangled"])

        tk = TupleAndKeywords.TupleAndKeywords()
        for argn in ctor.findall("Argument"):
            arg = Argument.Argument()
            arg.parse_xml(self.root, argn)
            tk.add_parameter(arg)

            self.fptrs.try_add(arg.type)

        self.ctors.append(tk)

    def _generate_constructors(self):
        name = self.namer.constructor(self.full_name)

        self.block.write_code(Code.Snippets.ctor_sig % {
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
            "CTOR_NAME": name,
        })

        with CodeBlock.BracketThis(self.block):
            if self.no_accessible_canonical_ctors:
                fmt = Code.Snippets.ctor_error_accessibility
                self.block.write_code(fmt % self.full_name)

                return

            if self._is_abstract():
                self.block.write_code(Code.Snippets.ctor_chk_abstract % {
                    "PYTYPE_NAME": self.namer.pytype(self.full_name),
                    "CLS_NAME": self.full_name,
                })


            pyside_debug_name = "%s::%s" % (self.full_name, self.name,)
            action = Code.Snippets.constructing % ((self.get_wrapt_class_name(),) * 2)

            if len(self.ctors) == 1:
                args = self.ctors[0]

                self._write_args_parsing_code(args, "return -1;", pyside_debug_name)
                self.block.write_code(action % args.get_parameters_string())
            else:
                self._write_overloads(name, self.ctors,
                                      err_return="return -1;",
                                      actions=(action,) * len(self.ctors),
                                      finish_directly=False,
                                      pyside_debug_name=pyside_debug_name)

            interfaces = Types.PythonAwareClassRegistry.find(self.full_name)
            if interfaces:
                self_setter = "self->cxx_obj->" + interfaces.self_setter
                self.block.write_code((self_setter % "(PyObject *) self") + ';')

            if self._require_wrapper_class():
                self.block.write_code("self->cxx_obj->self = self;")

            self.block.write_code(Code.Snippets.ctor_actions_more % (
                self.flags_assigner.assign(self.full_name)
            ))

            if self._get_lifetime_policy() == LT_CXX:
                self.block.write_code(Code.Snippets.ctor_incref)

            self.block.append_blank_line()
            self.block.write_code("return 0;")

    def _methods(self):
        args = (self.root, self.node.attrib["id"], self.allows_subclassing(), self.blacklist)
        for m in self.methods.process_class(*args):
            if m.virtual:
                self.virtual_members.append(m)
            elif m.access == Access.PROTECTED:
                decl = "using %s::%s;" % (self.full_name, m.name)
                self.protected_nonvirtual_members.add(decl)

        self.methods.collect_function_pointer_defs(self.fptrs)

    def _generate_methods(self):
        self.methods.generate_methods(self.block, self.namer, self)

    def _generate_method_table(self):
        self.methods.generate_method_table(self.block, self.namer, self)

    def allows_subclassing(self):
        return not (self.final or
                    self.no_accessible_canonical_ctors or
                    self.dtor_access_type == Access.PRIVATE or
                    self.enum_class)

    def _require_wrapper_class(self):
        if self.allows_subclassing():  # The first rule
            return (self.has_protected_ctor or
                    self.dtor_access_type == Access.PROTECTED or
                    len(self.protected_nonvirtual_members) > 0 or
                    len(self.virtual_members) > 0 or
                    self._get_lifetime_policy() == LT_CXX)

        return False

    def _is_abstract(self):
        for m in self.virtual_members:
            if m.pure_virtual:
                return True

        return False

    def _is_noncopyable(self):
        assert self.base_private_copy_ctor_checked

        # Copying an object whose class defines a proctected copy constructor
        # in the API code what we deal with is meaningless
        # TODO: public copy assignment operator
        return (self._is_abstract() or
                self.copy_ctor_access_type != Access.PUBLIC or
                self.arch_has_private_copy_ctor)

    def _expose_shadowed_non_virtuals(self):
        assert self.allows_subclassing()

        # Expose non-virtual methods shadowed by their virtual peers
        # overrode in the helper class

        concise_vm = set([vm.name for vm in self.virtual_members])

        for overloads in self.methods.methods.values():
            for m in overloads:
                if not m.virtual and m.name in concise_vm:
                    self.protected_nonvirtual_members.add(
                            "using %s::%s;" % (self.full_name, m.name
                        ))

                    if m.access == Access.PUBLIC:
                        self.public_nonvirtual_methods.append({
                            "DECL": "using %s::%s;" % (self.full_name, m.name),
                            "REF": m
                        })

        # Supplement with bases' shadowed public methods

        for bname in self.direct_bases:
            base = Registry.get_class(bname)

            for mm in base.public_nonvirtual_methods:
                # Subclass don't override this virtual member. Skip it.
                if mm["REF"].name in self.methods.methods:
                    self.protected_nonvirtual_members.add(mm["DECL"])
                    self.methods.methods[mm["REF"].name].append(mm["REF"])

            self.public_nonvirtual_methods += base.public_nonvirtual_methods

    def collect_virtual_members(self):
        if not self.base_vm_collected and self.allows_subclassing():
            virtual_members = []
            private_non_pure_virtuals = []

            for vm in self.virtual_members:
                if vm.access == Access.PRIVATE and not vm.pure_virtual:
                    private_non_pure_virtuals.append(vm)
                elif not vm.final:
                    virtual_members.append(vm)

            signitures = {vm.sig() for vm in self.virtual_members}

            for bname in self.direct_bases:
                for vm in Registry.get_class(bname).collect_virtual_members():
                    if vm.sig() not in signitures:
                        virtual_members.append(vm)

            self.virtual_members = virtual_members
            self.base_vm_collected = True

            self.methods.remove_private_non_pure_virtuals(private_non_pure_virtuals)
            self._expose_shadowed_non_virtuals()

        return self.virtual_members

    def check_bases_copy_ctors(self):
        if not self.base_private_copy_ctor_checked:
            if self.copy_ctor_access_type == Access.PRIVATE:
                self.arch_has_private_copy_ctor = True
            else:
                for base_full_name in self.direct_bases:
                    base = Registry.get_class(base_full_name)
                    if base.check_bases_copy_ctors():
                        self.arch_has_private_copy_ctor = True
                        break

            self.base_private_copy_ctor_checked = True

        return self.arch_has_private_copy_ctor

    def is_derived_from(self, base):
        if base in self.direct_bases:
            return True

        for b in self.direct_bases:
            if Registry.get_class(b).is_derived_from(base):
                return True

        return False

    def _generate_wrapper_class(self):
        assert self._require_wrapper_class()

        wrapper_name = self.namer.wrapper_class(self.full_name)
        self.block.write_code("class %s : public %s" % (
            wrapper_name, self.full_name
        ))

        with CodeBlock.BracketThis(self.block, postscript=';'):
            self.block.write_code("public:", temp_indent=0)
            self.block.write_code(self.namer.pyobj(self.full_name) + " *self = nullptr;")
            self.block.append_blank_line()

            if len(self.protected_nonvirtual_members) > 0:
                for m in sorted(self.protected_nonvirtual_members):
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

            if self._get_lifetime_policy() == LT_CXX:
                self.block.write_code(Code.Snippets.wrapper_dtor % wrapper_name)

            if len(self.virtual_members) == 0:
                self.block.lines = self.block.lines[:-1]  # Remove the trailing empty line
                return

            for m in sorted(self.virtual_members, lambda x, y: cmp(x.raw_sig, y.raw_sig)):
                pyside_debug_name = "%s %s" % (m.returns.decl(), m.raw_sig)

                if m.returns.decl()[-1] not in "&*":
                    fmt = "virtual %s %s(%s)%s"
                else:
                    fmt = "virtual %s%s(%s)%s"

                self.block.write_code(fmt % (
                    m.returns.decl(), m.name,
                    m.args.build_function_signature_parameter_list(),
                    " const" if m.raw_sig.endswith(" const") else "",
                ))

                memblock = CodeBlock.CodeBlock()
                names = []

                if m.args.size() > 0:
                    for arg in m.args.args:
                        pyname = "py_" + arg.name
                        names.append("(PyObject *) " + pyname)

                        memblock.write_code(arg.type.get_build_value_idecl(
                            arg.name, pyname, self.namer, raii=True
                        ))

                    memblock.append_blank_line()

                names.append("nullptr")

                with CodeBlock.BracketThis(self.block):
                    template_args = {
                        "WRAPT": self.full_name,
                        "SIG": m.raw_sig,
                        "MNAME": m.name,
                        "ARGS_COUNT": m.args.size(),
                        "ARGS": m.args.get_parameters_string(),
                        "BUILD_ARGS": memblock.flush(),
                        "CM_ARGS": ", ".join(names),
                        "RET": m.returns.decl(),
                        "EXCEPTION": "pbpp::CallPyMethodError",
                    }

                    h = Code.Snippets.virtual_method_wrapper_header(m.pure_virtual)
                    self.block.write_code(h % template_args)

                    if m.returns.decl() == "void":
                        self.block.write_code(Code.Snippets.handle_return_void % pyside_debug_name)
                    else:
                        err_handler = "PyErr_Print();\n"
                        err_handler += Code.Snippets.throw_cxxexception % template_args

                        self.block.write_code(m.returns.get_extractor_code(
                            "vm_retval", "py_vm_retval", err_handler, self.namer
                        ))

                        self.block.append_blank_line()
                        self.block.write_code("return vm_retval;")

    def _destructor(self):
        dtor = self.root.find("Destructor[@context='%s']" % self.node.attrib["id"])
        if dtor is not None:
            self.dtor_access_type = Access.access_type(dtor)

    def _generate_destructor(self):
        boilerplate = Code.Snippets.dealloc
        if ((self.dtor_access_type == Access.PROTECTED and not self._require_wrapper_class()) or
            (self.dtor_access_type == Access.PRIVATE)):
                boilerplate = Code.Snippets.dealloc_trivial

        self.block.write_code(boilerplate % {
            "DTOR_NAME": self.namer.destructor(self.full_name),
            "PYOBJ_NAME": self.namer.pyobj(self.full_name),
        })

        self.block.append_blank_line()


if __name__ == "__main__":
    pass
