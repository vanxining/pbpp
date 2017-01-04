#!/usr/bin/env python2

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


def fpt_action(args):
    if not args:
        return

    enable_logging()

    sys.path.insert(0,  os.path.abspath(curr_dir() + ".."))

    tests = ["pbpp.Tests.full_process.%s.test" % tc for tc in args.testcase]
    test_suite = unittest.defaultTestLoader.loadTestsFromNames(tests)

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


def run_all_tests(args):
    enable_logging()

    start_dir = os.path.abspath(curr_dir() + "Tests")
    toplevel_dir = os.path.abspath(curr_dir() + "..")

    test_suite = unittest.defaultTestLoader.discover(start_dir=start_dir,
                                                     top_level_dir=toplevel_dir)

    runner = unittest.TextTestRunner()
    runner.run(test_suite)


def main():
    parser = argparse.ArgumentParser("pbpp")
    subparsers = parser.add_subparsers(help="subcommands to perform")

    fp = subparsers.add_parser("fpt", help="run full process unit test(s)")
    fp.set_defaults(func=fpt_action)
    fp.add_argument("testcase", nargs='+', help="normally the name of the directory containing `test.py`")

    test = subparsers.add_parser("test", help="run all tests")
    test.set_defaults(func=run_all_tests)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
