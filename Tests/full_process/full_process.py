import importlib
import os
import shutil
import subprocess
import sys
import tempfile

import config
import customizers
from ... import Module
from ... import Registry
from ... import Xml


def _execute(cmd):
    return subprocess.call(cmd, shell=True)


# noinspection PyMethodMayBeStatic
class _TestCase(object):
    def __init__(self, tc_dir):
        assert tc_dir[-1] == os.path.sep

        self.tc_dir = tc_dir
        self.package_name = tc_dir[(tc_dir[:-1].rindex(os.path.sep) + 1):-1]
        self.tmp_dir = "{0}{1}pbpp{1}{2}{1}".format(
            tempfile.gettempdir(),
            os.path.sep,
            self.package_name
        )

    def _set_up(self):
        if not os.path.isdir(self.tmp_dir):
            os.makedirs(self.tmp_dir)

        shutil.copy(self.tc_dir + "def.hpp", self.tmp_dir + "def.hpp")
        for f in os.listdir(self.tc_dir):
            if f.endswith(".cpp"):
                shutil.copy(self.tc_dir + f, self.tmp_dir + f)

        shutil.copy(self.tc_dir + "../premake5.lua", self.tmp_dir + "premake5.lua")

        return self.tmp_dir + "def.hpp"

    def _clean(self):
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def _run_castxml(self, fcpp):
        xml_path = self.tmp_dir + os.path.basename(fcpp) + ".xml"
        cmd = '"%s" %s -o "%s" "%s"' % (
            config.castxml_bin,
            config.castxml_args,
            xml_path,
            fcpp,
        )

        rc = _execute(cmd)
        assert rc == 0
        assert os.path.exists(xml_path)

        return xml_path

    def _compress(self, fcpp, fxml):
        c = Xml.Compressor()
        c.compress((fcpp,), fxml, fxml)

    def _generate(self, fxml):
        try:
            m = Module.Module(self.package_name, None,
                              customizers.namer(self.package_name),
                              customizers.header_provider(),
                              customizers.flags_assigner(),
                              customizers.blacklist())

            Module.process_header(m, ("def.hpp",), fxml)

            m.finish_processing()
            m.generate(self.tmp_dir, ext=".cxx")
        except:
            raise
        finally:
            # Clear all saved classes
            Registry.clear()

    def _create_makefile(self):
        rc = _execute('"%s" gmake2 --targetname="%s" --pyroot="%s"' % (
            config.premake_bin, self.package_name, config.pyroot
        ))
        assert rc == 0

    def _build(self):
        rc = _execute(config.make)
        assert rc == 0

    def _import(self):
        return importlib.import_module(self.package_name)

    def _print_header(self):
        msg = "Testing %s... (full process)" % self.package_name

        print("\n\n")

        from logging import debug
        debug('*' * len(msg))
        debug(msg)
        debug('*' * len(msg))

        print("\n\n")

    def run(self):
        self._print_header()
        self._clean()

        owd = os.getcwd()

        try:
            fcpp = self._set_up()
            fxml = self._run_castxml(fcpp)
            self._compress(fcpp, fxml)
            self._generate(fxml)

            os.chdir(self.tmp_dir)
            self._create_makefile()
            self._build()

            sys.path.insert(0, self.tmp_dir)
            m = self._import()
        except:
            raise
        finally:
            if sys.path and sys.path[0] == self.tmp_dir:
                sys.path = sys.path[1:]

            os.chdir(owd)

        return m


def run(tc_dir):
    test_case = _TestCase(tc_dir)
    return test_case.run()


def run2(tc_file):
    tc_dir = os.path.split(tc_file)[0] + os.path.sep
    return run(tc_dir)
