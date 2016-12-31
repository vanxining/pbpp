import Types


def from_xml(root, node):
    arg = Argument()
    arg.parse_xml(root, node)

    return arg


class Argument(object):
    """Represents function argument as well as return type.
    """
    def __init__(self, ctype=None, name=None, defv=None, internal=False):
        assert ctype is None or isinstance(ctype, Types.Type)

        self.type = ctype
        self._set_name(name, internal)
        self.defv = defv

    def _set_name(self, name, internal=False):
        self.raw_name = name

        # TODO: Why name is None?
        if internal or name is None or not name.startswith("py_"):
            self.name = name
        else:
            self.name = '_' + name  # TODO: Customizable using a namer

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
