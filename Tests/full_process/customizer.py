import os

from ... import Class
from ... import Module


class Namer(Module.PythonNamer):
    def __init__(self, package_name):
        Module.PythonNamer.__init__(self)
        self.package_name = package_name

    def package(self):
        return self.package_name


class HeaderProvider(Module.HeaderProvider):
    def __init__(self):
        Module.HeaderProvider.__init__(self)

    def klass(self, cls):
        return "def.hpp",

    def module(self, name):
        return "def.hpp",


class FlagsAssigner(Module.FlagsAssigner):
    def assign(self, cls_name):
        return "pbpp::LifeTime::PYTHON"


class Blacklist(Module.Blacklist):

    _class_patterns = []

    _classes = {
        "PyObject",
        "_PySelf",
    }

    _base_patterns = []

    _bases = {
        "_PySelf",
    }

    _namespaces = {
        "std", "stdext", "__gnu_cxx",
    }

    _method_patterns = []

    _methods = {}

    _free_function_patterns = []
    _free_functions = {}

    _global_constants_patterns = []

    _global_constants = {}

    _fields = {}

    def __init__(self):
        Module.Blacklist.__init__(self)

    def klass(self, cls):
        for pattern in self._class_patterns:
            if pattern.match(cls):
                return True

        return cls in self._classes

    def base(self, full_name):
        for pattern in self._base_patterns:
            if pattern.match(full_name):
                return True

        return full_name in self._bases

    def namespace(self, ns):
        return ns in self._namespaces

    def method(self, mname):
        for pattern in self._method_patterns:
            if pattern.match(mname):
                return True

        return mname in self._methods

    def free_function(self, name):
        for pattern in self._free_function_patterns:
            if pattern.match(name):
                return True

        return name in self._free_functions

    def global_constants(self, full_decl_map):
        full_decl = "%s %s" % (full_decl_map["TYPE"], full_decl_map["FULL_NAME"])
        for pattern in self._global_constants_patterns:
            if pattern.match(full_decl):
                return True

        return full_decl_map["FULL_NAME"] in self._global_constants

    def field(self, cls, f):
        if f.startswith("m_") or f.startswith("sm_") or f.startswith("ms_"):
            return True
        else:
            return False


class ClassChanger(object):
    def __init__(self, cls):
        self.cls = cls

    def __enter__(self):
        if issubclass(self.cls, Namer):
            global namer
            namer = self.cls
        elif issubclass(self.cls, HeaderProvider):
            global header_provider
            header_provider = self.cls
        elif issubclass(self.cls, FlagsAssigner):
            global flags_assigner
            flags_assigner = self.cls
        elif issubclass(self.cls, Blacklist):
            global blacklist
            blacklist = self.cls
        else:
            raise RuntimeError("unknown subclass")

    def __exit__(self, exc_type, exc_value, traceback):
        if issubclass(self.cls, Namer):
            global namer
            namer = Namer
        elif issubclass(self.cls, HeaderProvider):
            global header_provider
            header_provider = HeaderProvider
        elif issubclass(self.cls, FlagsAssigner):
            global flags_assigner
            flags_assigner = FlagsAssigner
        elif issubclass(self.cls, Blacklist):
            global blacklist
            blacklist = Blacklist
        else:
            raise RuntimeError("unknown subclass")


namer = Namer
header_provider = HeaderProvider
flags_assigner = FlagsAssigner
blacklist = Blacklist
