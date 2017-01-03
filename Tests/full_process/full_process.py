import importlib
import os
import subprocess
import sys
import tempfile

import config
import customizer
from ... import Module
from ... import Registry
from ... import Util
from ... import Xml


tmp_dir = tempfile.gettempdir() + os.path.sep + "pbpp" + os.path.sep


def _execute(cmd):
    return subprocess.call(cmd, shell=True)


def _set_up(tc_dir):
    if not os.path.exists(tmp_dir) or not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    Util.smart_copy(tc_dir + "def.hpp", tmp_dir + "def.hpp")
    for f in os.listdir(tc_dir):
        if f.endswith(".cpp"):
            Util.smart_copy(tc_dir + f, tmp_dir + f)

    Util.smart_copy(tc_dir + "../premake5.lua", tmp_dir + "premake5.lua")

    return tmp_dir + "def.hpp"


def _run_castxml(fcpp):
    xml_path = tmp_dir + os.path.basename(fcpp) + ".xml"
    cmd = '%s %s -o "%s" "%s"' % (
        config.castxml_bin,
        config.castxml_args,
        xml_path,
        fcpp,
    )

    rc = _execute(cmd)
    assert rc == 0

    return xml_path


def _compress(fcpp, fxml):
    c = Xml.Compressor()
    c.compress((fcpp,), fxml, fxml)


def _generate(package_name, fxml):
    try:
        m = Module.Module(package_name, None,
                          customizer.namer(package_name),
                          customizer.header_provider(),
                          customizer.flags_assigner(),
                          customizer.blacklist())

        Module.process_header(m, ("def.hpp",), fxml)

        m.finish_processing()
        m.generate(tmp_dir, ext=".cxx")
    except:
        raise
    finally:
        # Clear all saved classes.
        Registry.clear()


def _create_makefile(package_name):
    rc = _execute('"%s" gmake --targetname="%s" --pyroot="%s"' % (
        config.premake_bin, package_name, config.pyroot
    ))
    assert rc == 0


def _build():
    rc = _execute(config.make)
    assert rc == 0


def _import(package_name):
    return importlib.import_module(package_name)


def _clean():
    obj_file = tmp_dir + "obj" + os.path.sep + "def.o"
    if os.path.exists(obj_file):
        os.remove(obj_file)

    for f in os.listdir(tmp_dir):
        if f.endswith(".py.cxx") or f.endswith(".cpp"):
            os.remove(tmp_dir + f)


def _print_header(package_name):
    msg = "Testing %s... (full process)" % package_name

    print("\n\n")

    from logging import debug
    debug('*' * len(msg))
    debug(msg)
    debug('*' * len(msg))

    print("\n\n")


def run(tc_dir):
    assert tc_dir[-1] == os.path.sep
    package_name = tc_dir[(tc_dir[:-1].rindex(os.path.sep) + 1):-1]

    _print_header(package_name)

    owd = os.getcwd()

    try:
        fcpp = _set_up(tc_dir)
        fxml = _run_castxml(fcpp)
        _compress(fcpp, fxml)
        _generate(package_name, fxml)

        os.chdir(tmp_dir)
        _create_makefile(package_name)
        _build()

        sys.path.insert(0, tmp_dir + package_name)
        m = _import(package_name)
    except:
        raise
    finally:
        if sys.path and sys.path[0] == tmp_dir + package_name:
            sys.path = sys.path[1:]

        _clean()
        os.chdir(owd)

    return m


def run2(tc_file):
    tc_dir = os.path.split(tc_file)[0] + os.path.sep
    return run(tc_dir)
