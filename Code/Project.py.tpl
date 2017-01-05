import os

import Converters
import Module
import ProjectBase
import Util


output_cxx_dir = r"%(GEN)s"
output_cxx_ext = ".cxx"

header_wrappers_dir = "{0}{1}Hacks{1}".format(os.path.dirname(__file__), os.path.sep)
header_wrappers_ext = ".pbpp.hpp"

castxml_bin = r'castxml'
_castxml_args = r'--castxml-output=1 -w -x c++ -std=c++14 -D__CASTXML__ -I"%(LIB)s"'


def castxml_args(header_path):
    if os.name == "nt":
        return _castxml_args + " -fms-compatibility-version=19"

    return _castxml_args


def select_headers(entry_header_path, xml_path):
    return entry_header_path,


class Project(ProjectBase.ProjectBase):
    def __init__(self):
        ProjectBase.ProjectBase.__init__(self, None)

        Converters.add(Converters.StrConv())
        Converters.add(Converters.WcsConv())

        %(PRJ)s = Util.load("%(PRJ)s")

        self.root_mod = Module.Module(
            "%(PRJ)s",
             None,
             %(PRJ)s.PythonNamer(),
             %(PRJ)s.HeaderProvider(),
             %(PRJ)s.FlagsAssigner(),
             %(PRJ)s.Blacklist()
        )

        pdl = %(PRJ)s.ProcessingDoneListener()
        self.root_mod.processing_done_listener = pdl

    def try_update(self):
        %(PRJ)s, reloaded = Util.load2("%(PRJ)s")

        if reloaded:
            self.root_mod.update_strategies(
                %(PRJ)s.PythonNamer(),
                %(PRJ)s.HeaderProvider(),
                %(PRJ)s.FlagsAssigner(),
                %(PRJ)s.Blacklist()
            )

            pdl = %(PRJ)s.ProcessingDoneListener()
            self.root_mod.processing_done_listener = pdl
