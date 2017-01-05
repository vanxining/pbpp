import unittest

from .. import customizers
from .. import full_process


class Blacklist(customizers.Blacklist):
    def global_constants(self, full_decl_map):
        if full_decl_map["FULL_NAME"] == "g_dp":
            return True

        return customizers.Blacklist.global_constants(self, full_decl_map)


class TestBlacklist(unittest.TestCase):
    def runTest(self):
        with customizers.ClassChanger(Blacklist):
            m = full_process.run2(__file__)

            self.assertFalse(m.g_invalid)
            self.assertFalse(hasattr(m, "g_dp"))
