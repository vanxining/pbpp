import os

import Methods
import Enum
import Code.Snippets
import CodeBlock
import HeaderJar
import Class


class PythonNamer:
    def __init__(self):
        pass

    def _to_python(self, name):
        raise NotImplementedError

    def fmt_path(self, cxxpath):
        namespaces = cxxpath.split("::")
        pythonic = []
        for ns in namespaces:
            if ns:
                pythonic.append(self._to_python(ns))

        return '.'.join(pythonic)


class OwnerAssigner:
    def __init__(self):
        pass


class HeaderProvider:
    def __init__(self):
        pass


class BlackList:
    def __init__(self):
        pass


class Module:

    _global_class_registry = {}
    _sorted = None

    @staticmethod
    def get_class(full_name):
        return Module._global_class_registry[full_name]

    @staticmethod
    def add_class(cls):
        assert isinstance(cls, Class.Class)
        Module._global_class_registry[cls.full_name] = cls

    @staticmethod
    def _sort_classes():
        class _Class:
            def __init__(self, klass):
                assert isinstance(klass, Class)

                self.ref = klass
                self.depends = [b for b in klass.bases]

                nester = klass.get_nester_class()
                if nester:
                    self.depends.append(nester)

        classes = [_Class(cls) for cls in Module._global_class_registry.values()]
        Module._sorted = []

        while len(classes) > len(Module._sorted):
            Module._do_sort_classes(classes)

    @staticmethod
    def _do_sort_classes(classes):
        for cls in classes:
            if cls.ref not in Module._sorted and len(cls.depends) == 0:
                Module._sorted.append(cls.ref)

                for s in Module._sorted:
                    for c in classes:
                        if c.ref not in Module._sorted and s.full_name in c.depends:
                            c.depends.remove(s.full_name)

                return

        print "====================================="
        print [cls.full_name for cls in Module._sorted]
        print [cls.full_name for cls in Module._global_class_registry.values()
               if cls not in Module._sorted]

        raise RuntimeError("Unexposed classes as base classes exist.")

    @staticmethod
    def finish_processing():
        Module._sort_classes()

        for cls in Module._global_class_registry.values():
            cls.collect_virtual_members()

    def __init__(self, name, parent, namer, header_provider, owner_assigner):
        self.name = name
        self.parent = parent
        self.context_id = None

        self.namer = namer
        self.header_provider = header_provider
        self.owner_assigner = owner_assigner

        self.submodules = {}
        self.classes = []
        self.enums = Enum.Enum()
        self.free_functions = Methods.MethodJar()
        self.globals = []

    def process_file(self, root):
        if self.parent:
            xpath = ".//Namespace[@name='%s'][@context='%s']" % (
                self.name, self.parent.context_id
            )

            self.context_id = root.find(xpath).attrib["id"]
        else:
            self.context_id = "_1"

        self.enums.process(root, self.context_id, self.namer)
        self._process_classes(root)
        self._process_free_functions(root)

        self._process_namespaces(root)

    def _cxx_namespace(self):
        ns = self.name if self.parent else ""

        ancestor = self.parent
        while ancestor:
            if ancestor.parent:
                ns = ancestor.name + "::" + ns

            ancestor = ancestor.parent

        return ns

    def _pyside_full_name(self):
        full_name = self.name

        ancestor = self.parent
        while ancestor:
            full_name = ancestor.name + '.' + full_name
            ancestor = ancestor.parent

        return full_name

    def get_creator_name(self):
        return self._pyside_full_name().replace('.', '_')

    def generate(self, outdir, ext):
        for submodule in self.submodules.values():
            submodule.generate(outdir, ext)

        #-------------------------------------------------------------------#

        block = CodeBlock.CodeBlock()

        block.write_code(self.header_provider.pch())
        header_jar = HeaderJar.HeaderJar()
        header_jar.add_headers(self.header_provider.module(self.name))
        if self.free_functions.require_type_info:
            header_jar.add_headers(("<typeinfo>",))

        mem_block = CodeBlock.CodeBlock()
        self.free_functions.generate_methods(mem_block, self.namer, cls=None)

        template_args = {
            "MNAME": self.name,
            "MNAME_FULL": self._pyside_full_name(),
            "FUNC_NAME": self.get_creator_name(),
            "HEADERS": '\n'.join(header_jar.headers),
            "FREE_FUNCTIONS": mem_block.flush(),
        }

        with open("Code/Header.inl", "rb") as inf:
            block.write_code(inf.read() % template_args)

        module_ptr = "__mod_" + self.get_creator_name().lower()

        block.write_code('extern "C" PyObject *%s = NULL;' % module_ptr)
        block.write_code(Code.Snippets.module_creator_header % template_args)

        block.indent()

        #-------------------------------------------------------------------#

        self.enums.generate(block, Code.Snippets.register_module_enum_values)

        for submodule in self.submodules.values():
            creator = submodule.get_creator_name()
            block.write_code("PyObject *%s(PyObject *parent);" % creator)
            block.write_code("%s(m);" % creator)
            block.append_blank_line()

        for cls in self.classes:
            cls.mod = 'm' if self.parent is None else module_ptr

        if self.parent is None:
            self._register_classes(block, outdir, ext)

        #-------------------------------------------------------------------#

        block.write_code(module_ptr + " = m;")
        block.write_code("return m;")

        block.unindent()
        block.write_code("}")

        if self.parent is None:
            block.write_lines(("", "", "EXPORT_MOD(%s)" % self.name, ""))

        path = "%s%s%s.py.%s" % (outdir, os.path.sep, self._pyside_full_name(), ext)
        with open(path, "wb") as outf:
            outf.write(block.flush())

    def _register_classes(self, block, outdir, ext):
        assert self.parent is None

        modules = set()
        declarations = []
        invoke = []

        for cls in self._sorted:
            if cls.mod != 'm':
                modules.add("extern PyObject *%s;" % cls.mod)

            register = self.namer.register(cls.full_name)
            declarations.append("void %s(PyObject *m);" % register)
            invoke.append("%s(%s);" % (register, cls.mod))
            del cls.mod

            cls.generate()

            pyside = self.namer.to_python(cls.full_name)
            path = "%s%s%s.py.%s" % (outdir, os.path.sep, pyside, ext)
            with open(path, "wb") as outf:
                outf.write(cls.block.flush())

        for lines in (declarations, modules, invoke):
            block.write_lines(lines)
            block.append_blank_line()

    def _process_namespaces(self, root):
        xpath = ".//Namespace[@context='%s']" % self.context_id

        for ns_node in root.findall(xpath):
            if ns_node.attrib["members"] == "":
                continue

            name = ns_node.attrib["name"]
            submodule = self.submodules.get(name, None)
            if not submodule:
                submodule = Module(name, self,
                                   self.namer,
                                   self.header_provider,
                                   self.owner_assigner)

                self.submodules[name] = submodule

            submodule.process_file(root)

    def _process_classes(self, root):
        self._do_process_classes(root, self.context_id)

    def _do_process_classes(self, root, context_id):
        for decl_type in ("Class", "Struct"):
            xpath = ".//%s[@file='f0'][@context='%s']" % (
                decl_type, context_id
            )

            for cls_node in root.findall(xpath):
                name = cls_node.attrib["name"]
                if "class_type_info" in name:
                    continue

                cls = Class.Class(root, cls_node, self)
                self.classes.append(cls)

                self._do_process_classes(root, cls_node.attrib["id"])

    def _process_free_functions(self, root):
        self.free_functions.process_free_functions(
            root, self.context_id, self._cxx_namespace()
        )


class wxPythonNamer(PythonNamer):
    @staticmethod
    def package():
        return "wx"

    def _to_python(self, name):
        name = name.split("::")[-1]

        if name.startswith("wx"):
            return name[2:]
        else:
            return name

    def to_python(self, name):
        return self.fmt_path(name).replace('.', '')

    def constructor(self, cls):
        name = self.to_python(cls)
        return "New" + name

    def destructor(self, cls):
        name = self.to_python(cls)
        return "Del" + name

    def pyobj(self, cls):
        name = self.to_python(cls)
        if name.islower():
            return "pseudo_" + name
        else:
            return "Pseudo" + name

    def pytype(self, cls):
        name = self.to_python(cls)
        if name.islower():
            return name + "_type"
        else:
            return name + "Type"

    def register(self, cls):
        name = self.to_python(cls)
        return "__" + name

    def wrapper_class(self, cls):
        name = self.to_python(cls)
        return name + "__PythonHelper"


class wxOwnerAssigner(OwnerAssigner):
    def __init__(self):
        OwnerAssigner.__init__(self)

    def assign(self, cls):
        return "wxBF_NONE"


class wxHeaderProvider(HeaderProvider):
    def __init__(self):
        HeaderProvider.__init__(self)

    def klass(self, cls):
        return 'X.h',

    def file(self, fname):
        return 'X.h',

    def module(self, name):
        return 'X.h',

    def pch(self):
        return '#include "StdAfx.hpp"'


class wxBlackList(BlackList):
    @staticmethod
    def can_expose(cls):
        return True


def test():
    import xml.etree.ElementTree as ET

    m = Module("Raw", None, wxPythonNamer(), wxHeaderProvider(), wxOwnerAssigner())
    m.process_file(ET.parse("wx.xml").getroot())
    m.finish_processing()

    m.generate(r'D:\CppSource\Temp\Raw\wx', ext="cxx")


if __name__ == "__main__":
    test()