import Types


def from_xml(root, node):
    arg = Argument()
    arg.parse_xml(root, node)
    return arg


class Argument:
    """Represents function argument as well as return type.
    """
    _unnamed_counter = 0

    def __init__(self, ctype=None, name=None, defv=None):
        assert ctype is None or isinstance(ctype, Types.Type)

        self.type = ctype
        self.name = name
        self.defv = defv

    def join_type_and_name(self):
        return self.type.declate_var(self.name, init=None)[:-1]

    def parse_xml(self, root, node):
        self.type = Types.get_type_from_id(node.attrib["type"], root)
        self.name = self._name(node)
        self.defv = self._defv(node)

    @staticmethod
    def _name(node):
        if "name" in node.attrib:
            return node.attrib["name"]
        else:
            Argument._unnamed_counter += 1
            return "_unused_%d" % Argument._unnamed_counter

    @staticmethod
    def _defv(node):
        if "default" in node.attrib:
            return node.attrib["default"]
        else:
            return None

if __name__ == "__main__":
    import xml.etree.ElementTree as ET

    _root = ET.parse("wx.xml").getroot()

    for _node in _root.findall("ReferenceType") + _root.findall("PointerType"):
        _ctype = Types.get_type_from_id(_node.attrib["id"], _root)
        print "%s: %s[%s]" % (_node.attrib["id"],
                              _ctype.decl(),
                              _ctype.decl_no_const())