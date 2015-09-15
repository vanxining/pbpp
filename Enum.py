import Access
from Util import context_of


class ScopedEnum:
    def __init__(self, name, full_name):
        self.name = name
        self.full_name = full_name
        self.values = {}
        self.instantiated = False


class Enum:
    def __init__(self):
        self.values = {}
        self.scoped_enums = {}

    def process(self, root, file_id, context, allows_protected, namer):
        count0 = len(self.values)
        se_count0 = len(self.scoped_enums)

        q = ".//Enumeration[@file='%s'][@context='%s']" % (file_id, context)

        for enum in root.findall(q):
            access = Access.access_type(enum)
            if access == Access.PRIVATE:
                continue

            if access == Access.PROTECTED and not allows_protected:
                continue

            ns_prefix = context_of(enum, root)
            if ns_prefix:
                ns_prefix += "::"

            if enum.attrib.get("scoped") == "1":
                se = ScopedEnum(enum.attrib["name"], ns_prefix + enum.attrib["name"])

                for v in enum.findall("EnumValue"):
                    name = v.attrib["name"]
                    cppv = "static_cast<int>(%s::%s)" % (se.full_name, name)
                    se.values[namer.to_python(name)] = cppv

                self.scoped_enums[se.name] = se
            else:
                for v in enum.findall("EnumValue"):
                    name = v.attrib["name"]
                    self.values[namer.to_python(name)] = ns_prefix + name

        return len(self.values) > count0 or len(self.scoped_enums) > se_count0

    def generate(self, block, action):
        if len(self.values) == 0:
            return

        block.write_code("EnumValue __values[] = {")
        block.indent()

        for name in sorted(self.values.keys()):
            block.write_code('{ "%s", %s },' % (name, self.values[name]))

        block.write_code("{  nullptr }")
        block.unindent()
        block.write_code("};")

        block.write_code(action)


def test_enum(file_id, context):
    enum = Enum()
    enum.process(r, file_id, context, VdkPythonNamer())

    for name in sorted(enum.values.keys()):
        print(name, "==>", enum.values[name])

    print("")

if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    r = ET.parse("Tests/Y.xml").getroot()

    from Console.VdkControls.VdkControls import VdkPythonNamer
    test_enum("f1", "_1")
    test_enum("f1", "_325")
