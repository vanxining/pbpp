import os
import xml.etree.ElementTree as ET
import Access
import Argument

import Fptr
import MethodJar
import Enum
import Code.Snippets
import CodeBlock
import HeaderJar
import Class
import Registry
import Session
import Util


class PythonNamer:
    def __init__(self):
        pass

    @staticmethod
    def package():
        raise NotImplementedError

    def fmt_path(self, cxxpath):
        namespaces = Util.split_namespaces(cxxpath)
        pythonic = []
        for ns in namespaces:
            if ns:
                pythonic.append(self._to_python(ns))

        return '.'.join(pythonic)

    @staticmethod
    def normalize_template(name):
        repl = (('const', '_const_'),
                ('<', '_'), ('>', '_'), ('::', '_'),
                (' ', ''),  (',', '_'), ('__', '_'),
                ('*', '_ptr'),)

        for pattern in repl:
            name = name.replace(*pattern)

        return name.rstrip("_")

    def _to_python(self, name):
        if '<' in name:
            name = PythonNamer.normalize_template(name)

        return name

    def to_python(self, name):
        return self.fmt_path(name).replace('.', '_')

    @staticmethod
    def constructor(cls):
        return "__init__"

    @staticmethod
    def destructor(cls):
        return "__del__"

    def adaptively_rename(self, cls, addin, prefix):
        name = self.to_python(cls)
        if name.islower():
            addin = addin.lower()

        return addin + "__" + name if prefix else name + "__" + addin

    def pyobj(self, cls):
        return self.adaptively_rename(cls, "Pseudo", prefix=True)

    def pytype(self, cls):
        return self.adaptively_rename(cls, "Type", prefix=False)

    def register(self, cls):
        name = self.to_python(cls)
        return "__" + name

    def borrower(self, cls):
        return self.adaptively_rename(cls, "Borrow", prefix=True)

    def copyer(self, cls):
        return self.adaptively_rename(cls, "Copy", prefix=True)

    def wrapper_class(self, cls):
        return self.adaptively_rename(cls, "PythonHelper", prefix=False)

    @staticmethod
    def free_function(name):
        return "__" + name

    @staticmethod
    def getter(field_name):
        return "__get_" + field_name

    @staticmethod
    def setter(field_name):
        return "__set_" + field_name


class FlagsAssigner:
    def __init__(self):
        pass

    def assign(self, cls_name):
        return "pbpp::LifeTime::PYTHON"


class HeaderProvider:
    def __init__(self):
        pass

    def klass(self, cls):
        return []

    @staticmethod
    def module(name):
        raise NotImplementedError()

    @staticmethod
    def normalize(full_path):
        raise NotImplementedError()

    @staticmethod
    def pch():
        return '#include "StdAfx.hpp"'


class BlackList:
    def __init__(self):
        pass

    def hook_write(self, name, content):
        return content

    def return_type(self, ret):
        return False


class Module:
    def __init__(self, name, parent, namer, header_provider, flags_assigner, blacklist):
        self.name = name
        self.parent = parent

        self.namer = namer
        self.header_provider = header_provider
        self.flags_assigner = flags_assigner
        self.blacklist = blacklist

        self.processing_done_listener = None

        self.submodules = {}
        self.classes = {}
        self.global_constants = {}
        self.enums = Enum.Enum()
        self.free_functions = MethodJar.MethodJar()
        self.header_jar = HeaderJar.HeaderJar()
        self.header_jar.add_headers(self.header_provider.module(self.name))

        self.modified = True

        # Only effective while processing a specified header
        self.root = None
        self.id = None
        self.file_node = None
        self.header_decl = None

    def is_root(self):
        return self.parent is None

    def prepare_for_serializing(self):
        self._clean()

        for cls in self.classes.values():
            cls.prepare_for_serializing()

    def _clean(self):
        self.root = None
        self.id = None
        self.file_node = None
        self.header_decl = None

    def update_strategies(self, namer, header_provider, flags_assigner, blacklist):
        self.namer = namer
        self.header_provider = header_provider
        self.flags_assigner = flags_assigner
        self.blacklist = blacklist

        for submodule in self.submodules.values():
            submodule.update_strategies(
                namer, header_provider, flags_assigner, blacklist
            )

    def _set_current_file(self, root, file_node):
        self.root = root

        if self.parent:
            xpath = ".//Namespace[@name='%s'][@context='%s']" % (
                self.name, self.parent.id
            )

            self.id = self.root.find(xpath).attrib["id"]
        else:
            self.id = "_1"

        self.file_node = file_node
        self.header_decl = self.header_provider.normalize(file_node.attrib["name"])

        self.header_jar.add_headers((self.header_decl,))

    def process_file(self, root, file_node):
        Session.begin(self.header_jar)

        self._set_current_file(root, file_node)

        self._process_global_constants()
        self._process_enums()
        self._process_inner_namespaces()
        self._process_free_functions()
        self._process_classes()

        Session.end()

    def current_file_id(self):
        return self.file_node.attrib["id"]

    def _process_global_constants(self):
        xpath = ".//Variable[@file='%s'][@context='%s']" % (
            self.current_file_id(), self.id
        )

        for var_node in self.root.findall(xpath):
            if "artificial" in var_node.attrib:
                if var_node.attrib["artificial"] == '1':
                    continue

            var = Argument.from_xml(self.root, var_node)
            var.name = var_node.attrib["demangled"]  # Full name

            full_decl = {
                "TYPE": var.type.decl(),
                "FULL_NAME": var.name
            }

            if self.blacklist.global_constants(full_decl):
                continue

            self.global_constants[var.name] = var
            self.modified = True

    def _process_enums(self):
        file_id = self.current_file_id()
        if self.enums.process(self.root, file_id, self.id, True, self.namer):
            self.modified = True

            for se in self.enums.scoped_enums.values():
                if not se.instantiated:
                    cls = Class.Class.instantiate_scoped_enum(se, self, None)
                    self.register_class(cls)

                    se.instantiated = True

    def register_class(self, cls):
        self.classes[cls.full_name] = cls
        Registry.add_class(cls)

    def _process_classes(self):
        self._do_process_classes(self.id)

    def _do_process_classes(self, context_id):
        for decl_type in ("Class", "Struct"):
            xpath = ".//%s[@file='%s'][@context='%s']" % (
                decl_type, self.current_file_id(), context_id
            )

            for cls_node in self.root.findall(xpath):
                full_name = cls_node.attrib["demangled"]

                if self.blacklist.klass(full_name):
                    Session.ignored_classes.add(full_name)
                    continue

                if self.blacklist.dummy_klass(full_name):
                    Session.dummy_classes.add(full_name)
                    continue

                if Access.access_type(cls_node) == Access.PRIVATE:
                    continue

                if cls_node.attrib.get("incomplete", None) == "1":
                    continue

                print("")
                print("---------------------------------------------")
                print(">>> %s <<<" % full_name)
                print("---------------------------------------------")

                cls = Class.Class(self.root, cls_node, self)
                self.register_class(cls)

                print("---------------------------------------------")
                print("")

                self._do_process_classes(cls_node.attrib["id"])

                self.modified = True

    def _get_cxx_namespace(self):
        if self.parent:
            ns = self.name

            ancestor = self.parent
            while ancestor:
                if ancestor.parent:
                    ns = ancestor.name + "::" + ns

                ancestor = ancestor.parent

            return ns
        else:
            return ""

    def _process_free_functions(self):
        if self.free_functions.process_free_functions(
            self.root, self.file_node.attrib["id"],
            self.id, self._get_cxx_namespace(),
            self.blacklist
        ):
            self.modified = True

    def _process_inner_namespaces(self):
        xpath = ".//Namespace[@context='%s']" % self.id

        for ns_node in self.root.findall(xpath):
            if "name" not in ns_node.attrib:  # TODO: Anonymous namespace
                continue

            if len(ns_node.attrib["members"]) == 0:
                continue

            full_name = ns_node.attrib["demangled"]
            if self.blacklist.namespace(full_name):
                Session.ignored_namespaces.add(full_name)
                continue

            name = ns_node.attrib["name"]
            submodule = self.submodules.get(name, None)
            if not submodule:
                submodule = Module(name, self,
                                   self.namer,
                                   self.header_provider,
                                   self.flags_assigner,
                                   self.blacklist)

                self.submodules[name] = submodule

            submodule.process_file(self.root, self.file_node)
            self.modified = True

    def _pyside_full_name(self):
        full_name = self.name

        ancestor = self.parent
        while ancestor:
            full_name = ancestor.name + '.' + full_name
            ancestor = ancestor.parent

        return full_name

    def get_creator_name(self):
        return self._pyside_full_name().replace('.', '_')

    def _generate_global_constants_wrapper(self, block):
        forward_decl = set()
        memblock = CodeBlock.CodeBlock()
        usable_id = 6329

        for name in sorted(self.global_constants.keys()):
            const = self.global_constants[name]

            if not const.type.is_trivial() and not const.type.cvt:
                borrower = self.namer.borrower(const.type.intrinsic_type())
                forward_decl.add("PyObject *%s(const %s &);" % (
                    borrower, const.type.intrinsic_type()
                ))

                memblock.write_code('PyModule_AddObject(m, "%s", %s(%s%s));' % (
                    self.namer.to_python(const.name), borrower,
                    '*' if const.type.is_ptr() else "",
                    const.name
                ))
            else:
                # TODO: Review

                bld = const.type.get_build_value_idecl(const.name, namer=self.namer)
                one_line = '\n' not in bld

                if one_line:
                    arg = bld[(16 + len(const.name)):-1]
                else:
                    py_var_name = "__var_%d" % usable_id
                    usable_id += 1

                    bld = const.type.get_build_value_idecl(const.name, py_var_name, namer=self.namer)

                    memblock.append_blank_line()
                    memblock.write_code(bld)
                    arg = py_var_name

                memblock.write_code('PyModule_AddObject(m, "%s", %s);' % (
                    self.namer.to_python(const.name), arg
                ))

                if not one_line:
                    memblock.append_blank_line()

        if len(forward_decl) > 0:
            block.write_lines(forward_decl)
            block.append_blank_line()

        block.write_code(Code.Snippets.register_global_constants_sig)
        with CodeBlock.BracketThis(block):
            block.write_code(memblock.flush())

    def _generate_enums_register(self, block):
        block.write_code(Code.Snippets.module_register_enums_sig)
        with CodeBlock.BracketThis(block):
            self.enums.generate(block, Code.Snippets.register_module_enum_values)

    def _create_dummy_wrappers(self):
        assert self.header_decl is None

        myns = self._get_cxx_namespace()
        down = False

        for ddef in self.blacklist.dummy_classes.values():
            if Registry.get_class(ddef.full_name):
                continue

            if ddef.namespace != myns:
                down = True
                continue

            cls = Class.Class(self.root, None, self, ddef)
            if ddef.header:
                cls.set_header(ddef.header)

            self.register_class(cls)
            self.modified = True

        if down:
            for submodule in self.submodules:
                submodule._create_dummy_wrappers()

    def finish_processing(self):
        self._clean()

        self._create_dummy_wrappers()

        if self.is_root():
            self._add_predefined_symbols()
            Registry.sort_out()

        if self.processing_done_listener:
            self.processing_done_listener.on_processing_done(self)

    def _add_predefined_symbols(self):
        pass

    def _copy_helpers(self, outdir):
        dir_path = os.path.dirname(__file__) + "/Helpers/"
        for f in os.listdir(dir_path):
            local = dir_path + f
            remote = outdir + '/' + f

            content = open(local).read()
            if f.endswith(".cxx"):
                content = self.header_provider.pch() + '\n' + content

            Util.smart_write(remote, content)

    def generate(self, outdir, ext):
        for submodule in self.submodules.values():
            submodule.generate(outdir, ext)

        Session.begin(self.header_jar)

        output_path = "%s%s%s.py%s" % (
            outdir, os.path.sep, self._pyside_full_name(), ext
        )

        if self.is_root():
            self._copy_helpers(outdir)

        if not self.modified and os.path.exists(output_path):
            return

        fp_mem_block = CodeBlock.CodeBlock()
        fptrs = Fptr.FptrManager()
        self.free_functions.collect_function_pointer_defs(fptrs)
        if not fptrs.empty():
            fptrs.generate(fp_mem_block)
            fp_mem_block.append_blank_line()
            fp_mem_block.append_blank_line()

        ff_mem_block = CodeBlock.CodeBlock()
        self.free_functions.generate_methods(ff_mem_block, self.namer, cls=None)

        template_args = {
            "MNAME": self.name,
            "MNAME_FULL": self._pyside_full_name(),
            "FUNC_NAME": self.get_creator_name(),
            "HEADERS": self.header_jar.concat_sorted(),
            "FPTRS": fp_mem_block.flush(),
            "FREE_FUNCTIONS": ff_mem_block.flush(),
        }

        block = CodeBlock.CodeBlock()
        block.write_code(self.header_provider.pch())

        with open(os.path.dirname(__file__) + "/Code/Header.inl", "r") as f:
            block.write_code(f.read() % template_args)

        self._generate_global_constants_wrapper(block)
        self._generate_enums_register(block)

        module_ptr = "__mod_" + self.get_creator_name().lower()

        block.write_code('extern "C" PyObject *%s = nullptr;' % module_ptr)
        block.write_code(Code.Snippets.module_creator_header % template_args)
        block.indent()

        block.write_code("__Globals(m);")
        block.write_code("__Enums(m);")
        block.append_blank_line()

        for submodule in self.submodules.values():
            creator = submodule.get_creator_name()
            block.write_code("PyObject *%s(PyObject *parent);" % creator)

        if len(self.submodules) > 1:
            block.append_blank_line()

        for submodule in self.submodules.values():
            creator = submodule.get_creator_name()
            block.write_code("%s(m);" % creator)

        if len(self.submodules) > 1:
            block.append_blank_line()

        for cls in self.classes.values():
            cls.mod = 'm' if self.is_root() else module_ptr

        if self.is_root():
            self._register_classes(block, outdir, ext)

        block.write_code(module_ptr + " = m;")
        block.write_code("return m;")
        block.unindent()
        block.write_code("}")

        if self.is_root():
            block.write_lines(("", "", "EXPORT_MOD(%s)" % self.name, ""))


        ns = self._get_cxx_namespace() or self.name
        content = self.blacklist.hook_write(ns, block.flush())

        Util.smart_write(output_path, content)

        self.modified = False

        Session.end()

    def mark_as_dirty(self):
        self.modified = True

        for cls in self.classes.values():
            cls.modified = True

        for submodule in self.submodules.values():
            submodule.mark_as_dirty()

    def _register_classes(self, block, outdir, ext):
        assert self.is_root()

        modules = set()
        declarations = []
        invoke = []

        for cls in Registry.get_sorted():
            if cls.mod != 'm':
                modules.add("extern PyObject *%s;" % cls.mod)

            register = self.namer.register(cls.full_name)
            declarations.append("void %s(PyObject *m);" % register)
            invoke.append("%s(%s);" % (register, cls.mod))

            pyside = self.namer.to_python(cls.full_name)
            path = "%s%s%s.py%s" % (outdir, os.path.sep, pyside, ext)

            if cls.modified or not os.path.exists(path):
                cls.generate()

                content = cls.block.flush()
                content = self.blacklist.hook_write(cls.full_name, content)

                Util.smart_write(path, content)

        for lines in (declarations, modules, invoke):
            block.write_lines(lines)
            block.append_blank_line()


def process_header(mod, headers, fxml):
    assert isinstance(headers, (tuple, list, set))

    root = ET.parse(fxml).getroot()

    for fnode in root.findall("File"):
        if os.path.split(fnode.attrib["name"])[1] in headers:  # TODO:
            mod.process_file(root, fnode)
