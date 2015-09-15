import Types


def from_xml(root, node):
    arg = Argument()
    arg.parse_xml(root, node)

    return arg


class Argument:
    """Represents function argument as well as return type.
    """

    _predefined = (
        # argument common
        "self", "args", "kwargs",

        # function common
        "obj", "exceptions", "exdtor", "_saved", # wxPyBeginAllowThreads
        "i", "cnt",  # loop iterator

        # virtual function
        "py_method", "py_method_name", "_blocker",
        "vm_retval", "py_vm_retval",

        # getter & setter
        "py_value", "py_closure",
    )

    def __init__(self, ctype=None, name=None, defv=None, internal=False):
        assert ctype is None or isinstance(ctype, Types.Type)

        self.type = ctype
        self._set_name(name, internal)
        self.defv = defv

    def _set_name(self, name, internal=False):
        self.raw_name = name
        if internal or name not in Argument._predefined:
            self.name = name
        else:
            self.name = name + '0'

    def parse_xml(self, root, node):
        self.type = Types.get_type_by_id(node.attrib["type"], root)
        self._set_name(self._name_from_xml(node))
        self.defv = self._defv_from_xml(node)

    def join_type_and_name(self):
        return self.type.declare_var(self.name, init=None)[:-1]

    @staticmethod
    def _name_from_xml(node):
        return node.attrib.get("name", "")

    @staticmethod
    def _defv_from_xml(node):
        return node.attrib.get("default")

if __name__ == "__main__":
    import xml.etree.ElementTree as ET

    _root = ET.parse("Console/Raw/Xml/V.xml").getroot()

    n = _root.find(".//Method[@id='_185']")[0]
    a = from_xml(_root, n)

    print a.type.declare_var(a.name, a.defv)
