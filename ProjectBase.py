import cPickle as pickle
import logging
import os
import shutil
import tempfile

import Registry


# noinspection PyBroadException
class ProjectBase(object):
    def __init__(self, root_mod):
        self.root_mod = root_mod
        self.parsed = set()

        Registry.clear()

    def load(self, path):
        try:
            with open(path, "rb") as inf:
                self.root_mod = pickle.load(inf)
                Registry.clear()
                Registry.restore_from_module(self.root_mod)
                self.parsed = pickle.load(inf)

                return True
        except:
            logging.exception("Failed to load state snapshot file")

            return False

    def save(self, path):
        try:
            with open(path, "wb") as outf:
                self.root_mod.prepare_for_serializing()
                pickle.dump(self.root_mod, outf)
                pickle.dump(self.parsed, outf)

                return True
        except:
            logging.exception("Failed to save state snapshot file")

            return False

    def mark_as_parsed(self, header):
        self.parsed.add(header)

    def try_update(self):
        pass

    @staticmethod
    def xml_file_canonical_name(header_path):
        full_name = os.path.split(header_path)[-1]
        return full_name[:full_name.rindex('.')].upper()


def get_temp_cpp_header_path(header_path):
    short_name = os.path.split(header_path)[1]
    return tempfile.gettempdir() + os.sep + short_name + ".pbpp.hh"


def make_temp_cpp_header(header_path):
    if os.path.splitext(header_path)[1] in (".H", ".hpp", ".hh"):
        return header_path

    temp_header = get_temp_cpp_header_path(header_path)
    shutil.copy(header_path, temp_header)

    return temp_header


def remove_possible_temp_cpp_header(header_path):
    temp_header = get_temp_cpp_header_path(header_path)
    if os.path.exists(temp_header):
        os.remove(temp_header)
