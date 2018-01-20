#! python2.7-32

import argparse
import logging
import os
import sys
import unittest


def curr_dir():
    return os.path.dirname(__file__) + os.path.sep


def enable_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%m-%d %H:%M")


def run_specified_tests(args, module_fmt):
    if not args:
        return

    enable_logging()

    sys.path.insert(0, os.path.abspath(curr_dir() + ".."))

    tests = [module_fmt % tc for tc in args.testcase]
    test_suite = unittest.defaultTestLoader.loadTestsFromNames(tests)

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


def run_simple_unit_tests(args):
    run_specified_tests(args, "pbpp.Tests.test_%s")


def run_full_process_tests(args):
    run_specified_tests(args, "pbpp.Tests.full_process.%s.test")


def run_all_tests(args):
    enable_logging()

    start_dir = os.path.abspath(curr_dir() + "Tests")
    toplevel_dir = os.path.abspath(curr_dir() + "..")

    test_suite = unittest.defaultTestLoader.discover(start_dir=start_dir,
                                                     top_level_dir=toplevel_dir)

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


def start_new_project(args):
    enable_logging()

    lib = raw_input("Please input the directory containing the library to wrap: ")
    gen = raw_input("Please input the directory that will store the generated C++ source files: ")

    for d in (lib, gen,):
        while d and d[-1] in r"\/":
            d = d[:-1]

    if os.path.exists(args.name) and not os.path.isdir(args.name):
        logging.error("Cannot create project directory: a file with the desired name exists")
        return

    proj_dir = args.name + os.path.sep

    for d in ("", "Hacks", "Xml", "Premake",):
        if not os.path.exists(proj_dir + d):
            os.mkdir(proj_dir + d)

    if not os.path.exists(gen):
        os.makedirs(gen)

    for f in ("__init__.py", "Headers.lst",):
        open(proj_dir + f, 'a').close()

    template_dir = "{0}{1}Code{1}".format(os.path.dirname(__file__), os.path.sep)
    template_args = {
        "PRJ": args.name,
        "LIB": lib,
        "GEN": gen,
    }

    with open(proj_dir + "Project.py", "w") as outf:
        outf.write(open(template_dir + "Project.py.tpl").read() % template_args)

    with open(proj_dir + args.name + ".py", "w") as outf:
        outf.write(open(template_dir + "Customizers.py.tpl").read() % template_args)

    for key in template_args:
        template_args[key] = template_args[key].replace('\\', '/')

    with open("{0}{1}Premake{1}premake5.lua".format(proj_dir, os.path.sep), "w") as outf:
        outf.write(open(template_dir + "premake5.lua.tpl").read() % template_args)

    logging.info("PyBridge++ binding project `%s` created successfully.", args.name)


def main():
    parser = argparse.ArgumentParser("pbpp")
    subparsers = parser.add_subparsers(help="subcommands to perform")

    ut = subparsers.add_parser("ut", help="run simple unit test(s)")
    ut.set_defaults(func=run_simple_unit_tests)
    ut.add_argument("testcase", nargs='+',help="the name of the test (XXX in test_XXX.py)")

    fpt = subparsers.add_parser("fpt", help="run full process unit test(s)")
    fpt.set_defaults(func=run_full_process_tests)
    fpt.add_argument("testcase", nargs='+', help="the name of the directory containing `test.py`")

    test = subparsers.add_parser("test", help="run all tests")
    test.set_defaults(func=run_all_tests)

    startproject = subparsers.add_parser("startproject", help="start a new PyBridge++ binding project")
    startproject.set_defaults(func=start_new_project)
    startproject.add_argument("name", help="the name of the project")

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
