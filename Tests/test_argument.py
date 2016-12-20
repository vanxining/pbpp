
import unittest
import xml.etree.ElementTree as ET

from .. import Argument


class TestArgument(unittest.TestCase):
    def runTest(self):
        root = ET.parse("Tests/raw/Y.xml").getroot()

        node = root.find(".//Method[@id='_6570']")[0]
        arg = Argument.from_xml(root, node)

        self.assertEqual(arg.type.declare_var(arg.name, arg.defv), "Y *y;")
