import importlib
import os
import subprocess
import tempfile

import config
import customizer
from ... import Module
from ... import Registry
from ... import Util
from ... import Xml


tmp_dir = tempfile.gettempdir() + os.path.sep + "pbpp" + os.path.sep


def _set_up(tc_dir):
    if not os.path.exists(tmp_dir) or not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    Util.smart_copy(tc_dir + "def.hpp", tmp_dir + "def.hpp")
    for f in os.listdir(tc_dir):
        if f.endswith(".cpp"):
            Util.smart_copy(tc_dir + f, tmp_dir + f)

    Util.smart_copy(tc_dir + "../premake5.lua", tmp_dir + "premake5.lua")

    return tmp_dir + "def.hpp"


def _run_gccxml(fcpp):
    xml_path = tmp_dir + os.path.basename(fcpp) + ".xml"
    cmd = '%s %s -o "%s" "%s"' % (
        config.gccxml_bin,
        config.gccxml_args,
        xml_path,
        fcpp,
    )

    rc = subprocess.call(cmd)
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
    rc = subprocess.call('"%s" gmake --targetname="%s" --pyroot="%s"' % (
        config.premake_bin, package_name, config.pyroot
    ))
    assert rc == 0


def _build():
    rc = subprocess.call(config.make)
    assert rc == 0


def _import(package_name):
    return importlib.import_module(package_name)


def _clean():
    for root, _, files in os.walk(tmp_dir):
        for f in files:
            if f.endswith(".py.cxx"):
                os.remove(tmp_dir + f)


def _print_header(package_name):
    msg = "Testing %s... (full process)" % package_name

    print("\n\n")
    print('*' * len(msg))
    print(msg)
    print('*' * len(msg))
    print("\n\n")


def run(tc_dir):
    assert tc_dir[-1] == os.path.sep
    package_name = tc_dir[(tc_dir[:-1].rindex(os.path.sep) + 1):-1]

    _print_header(package_name)

    fcpp = _set_up(tc_dir)
    fxml = _run_gccxml(fcpp)
    _compress(fcpp, fxml)
    _generate(package_name, fxml)

    owd = os.getcwd()

    try:
        os.chdir(tmp_dir)
        _create_makefile(package_name)
        _build()

        os.chdir(tmp_dir + package_name)
        m = _import(package_name)
    except:
        raise
    finally:
        _clean()
        os.chdir(owd)

    return m


def run2(tc_file):
    tc_dir = os.path.split(tc_file)[0] + os.path.sep
    return run(tc_dir)
