import Access
import Util


class ScopedEnum(object):
    def __init__(self, name, full_name):
        self.name = name
        self.full_name = full_name
        self.values = {}
        self.instantiated = False


class Enum(object):
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

            ns_prefix = Util.context_of(enum, root)
            if ns_prefix:
                ns_prefix += "::"

            if enum.attrib.get("scoped") == "1":
                se = ScopedEnum(enum.attrib["name"], ns_prefix + enum.attrib["name"])

                for v in enum.findall("EnumValue"):
                    name = v.attrib["name"]
                    cppv = "%s::%s" % (se.full_name, name)
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

        block.write_code("static pbpp::EnumValue s_values[] = {")
        block.indent()

        for name in sorted(self.values.keys()):
            block.write_code('{ "%s", static_cast<int>(%s) },' % (name, self.values[name]))

        block.write_code("{  nullptr }")
        block.unindent()
        block.write_code("};")

        block.write_code(action)
