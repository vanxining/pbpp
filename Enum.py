__author__ = 'wxn'

from Util import context_of


class Enum:
    class Value:
        def __init__(self, name, value):
            self.name = name
            self.val = value

    def __init__(self):
        self.values = []

    def process(self, root, context, namer):
        ns_prefix = None

        for enum in root.findall(".//Enumeration[@file='f0'][@context='%s']" % context):
            if ns_prefix is None:
                ns_prefix = context_of(enum, root)
                if ns_prefix:
                    ns_prefix += "::"

            for val in enum.findall("EnumValue"):
                self.values.append(Enum.Value(
                    namer.to_python(val.attrib['name']),
                    ns_prefix + val.attrib['name'],
                ))

    def generate(self, block, action):
        if len(self.values) == 0:
            return

        block.write_code("EnumValue __values[] = {")
        block.indent()

        for val in self.values:
            block.write_code('{ "%s", %s },' % (val.name, val.val))

        block.write_code("{  NULL }")
        block.unindent()
        block.write_code("};")

        block.write_code(action)


def test_enum():
    enum = Enum()
    enum.process(r, "_1", wxPythonNamer())
    for val in enum.values:
        print val.name, "==>", val.val

    enum = Enum()
    enum.process(r, "_90", wxPythonNamer())
    for val in enum.values:
        print val.name, "==>", val.val


if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    from Module import wxPythonNamer

    r = ET.parse("wx.xml").getroot()

    test_enum()