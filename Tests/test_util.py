import unittest
import xml.etree.ElementTree as ET

from .. import Util


class TestUtil(unittest.TestCase):
    def test_split_namespaces(self):
        result = Util.split_namespaces("std::vector<int, std::allocator<int> >")
        self.assertEqual(result, ["std", "vector<int, std::allocator<int> >"])

        result = Util.split_namespaces("std::vector<std::allocator<std::size_t>, std::allocator<int> >::const_iterator")
        self.assertEqual(result, ["std", "vector<std::allocator<std::size_t>, std::allocator<int> >", "const_iterator"])

    def test_xml_related(self):
        root = ET.parse("Tests/raw/V.xml").getroot()

        for node_id in ("_35",):
            node = root.find(".//*[@id='%s']" % node_id)

            self.assertEqual(Util.context_of(node, root), "K")
            self.assertEqual(Util.full_name_of(node, root), "K::KK")
