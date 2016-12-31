import unittest
import os
import xml.etree.ElementTree as ET

from namer import TestNamer

from .. import Enum
from .. import CodeBlock


class TestEnum(unittest.TestCase):
    def runTest(self):
        root = ET.parse(os.path.dirname(__file__) + "/raw/V.xml").getroot()
        namer = TestNamer()

        enum = Enum.Enum()
        enum.process(root, "f1", "_1", allows_protected=False, namer=namer)

        se = enum.scoped_enums.get("EnumClass", None)
        self.assertIsNotNone(se)
        self.assertEqual(se.full_name, "EnumClass")

        block = CodeBlock.CodeBlock()
        enum.generate(block, "")
        self.assertEqual(block.flush(), '''static pbpp::EnumValue s_values[] = {
    { "V_IN", static_cast<int>(V_IN) },
    { "V_OUT", static_cast<int>(V_OUT) },
    {  nullptr }
};''')
