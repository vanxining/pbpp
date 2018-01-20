import unittest
import xml.etree.ElementTree as ET

from namer import TestNamer

from .. import CodeBlock
from .. import Enum
from .. import Types


class TestEnum(unittest.TestCase):
    def test_enum(self):
        root = ET.parse("Tests/raw/V.xml").getroot()
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

    def test_enum_ptr(self):
        root = ET.parse("Tests/raw/ENUM_PTR.xml").getroot()
        namer = TestNamer()

        tp = Types.get_type_by_id("_19", root)
        self.assertEqual(tp.decl(), "Shape *")
        self.assertEqual(
            tp.get_build_value_idecl("shape", namer=namer),
            'PyObject *py_shape = shape ? PyCapsule_New((void *) shape, "Shape *", nullptr) : Py_None;'
        )

        tp = Types.get_type_by_id("_23", root)
        self.assertEqual(tp.decl(), "Color const *")
        self.assertEqual(
            tp.get_build_value_idecl("color", namer=namer),
            'PyObject *py_color = color ? PyCapsule_New((void *) color, "Color *", nullptr) : Py_None;'
        )

        tp = Types.get_type_by_id("_11", root)
        self.assertEqual(tp.decl(), "Color &")
        self.assertEqual(
            tp.get_build_value_idecl("color", namer=namer),
            'PyObject *py_color = PyCapsule_New((void *) &color, "Color &", nullptr);'
        )

    def runTest(self):
        self.test_enum()
        self.test_enum_ptr()
