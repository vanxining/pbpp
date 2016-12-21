import cPickle as pickle
import os
import shutil
import tempfile

import Registry


class ProjectBase(object):
    def __init__(self, root_mod):
        self.root_mod = root_mod
        self.parsed = set()

        Registry.clear()

    def save(self, path):
        assert self.root_mod is not None
        with open(path, "wb") as outf:
            self.root_mod.prepare_for_serializing()
            pickle.dump(self.root_mod, outf)
            pickle.dump(self.parsed, outf)

    def load(self, path):
        with open(path, "rb") as inf:
            self.root_mod = pickle.load(inf)
            Registry.clear()
            Registry.restore_from_module(self.root_mod)
            self.parsed = pickle.load(inf)

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
