import os
import re

import Class
import Registry
import Module


# noinspection PyMethodMayBeStatic
class PythonNamer(Module.PythonNamer):
    def package(self):
        return "%(PRJ)s"


# noinspection PyMethodMayBeStatic
class HeaderProvider(Module.HeaderProvider):
    def __init__(self):
        Module.HeaderProvider.__init__(self)


class FlagsAssigner(Module.FlagsAssigner):

    _managed_by_cxx = ()

    def assign(self, cls_name):
        cls = Registry.get_class(cls_name)

        for nonowned in self._managed_by_cxx:
            if cls.full_name == nonowned or cls.is_derived_from(nonowned):
                return "pbpp::LifeTime::CXX"

        return "pbpp::LifeTime::PYTHON"


# noinspection PyMethodMayBeStatic
class Blacklist(Module.Blacklist):

    _namespace_patterns = ()
    _namespaces = {
        "std", "stdext", "__gnu_cxx",
        "__castxml",
    }

    _class_patterns = ()
    _classes = {
        "PyObject",
        "_PySelf",
    }

    _base_patterns = ()
    _bases = {
        "_PySelf",
    }

    _method_patterns = ()
    _methods = ()

    _free_function_patterns = ()
    _free_functions = ()

    _return_type_patterns = ()
    _return_types = ()

    _global_constants_patterns = ()
    _global_constants = ()

    _field_patterns = ()
    _fields = ()

    def __init__(self):
        Module.Blacklist.__init__(self)

        for cls in ():
            self.add_simple_dummy_class(cls)

    def namespace(self, ns):
        for pattern in self._namespace_patterns:
            if pattern.match(ns):
                return True

        return ns in self._namespaces

    def klass(self, cls):
        for pattern in self._class_patterns:
            if pattern.match(cls):
                return True

        return cls in self._classes

    def dummy_class(self, cls):
        return cls in self.dummy_classes

    def base(self, full_name):
        for pattern in self._base_patterns:
            if pattern.match(full_name):
                return True

        return full_name in self._bases

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

    def return_type(self, ret):
        for pattern in self._return_type_patterns:
            if pattern.match(ret):
                return True

        return ret in self._return_types

    def global_constants(self, full_decl_map):
        full_decl = "%%s %%s" %% (full_decl_map["TYPE"], full_decl_map["FULL_NAME"])
        for pattern in self._global_constants_patterns:
            if pattern.match(full_decl):
                return True

        return full_decl_map["FULL_NAME"] in self._global_constants

    def field(self, cls, f):
        if f.startswith("m_") or f.startswith("sm_") or f.startswith("ms_"):
            return True

        decl = cls + "::" + f

        for pattern in self._field_patterns:
            if pattern.match(decl):
                return True

        return decl in self._fields


# noinspection PyMethodMayBeStatic
class ProcessingDoneListener:
    def __init__(self):
        pass

    def on_processing_done(self, module):
        X_Inject = module.free_functions.methods.pop("X_Inject", None)
        if X_Inject:
            X = Registry.get_class("X")
            X.inject_as_method(X_Inject, "Inject", None)
