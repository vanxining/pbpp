import xml.etree.ElementTree as ET


def load(inf):
    Compressor.load(inf)


def save(outf):
    Compressor.save(outf)


def clear():
    Compressor.clear()


def get_file_node(root, fpath):
    for fnode in root.findall("File"):
        if fnode.attrib["name"] == fpath:
            return fnode

    assert False


class Compressor:

    class BlackList:
        def __init__(self):
            pass

        def base(self, full_name):
            raise NotImplementedError


    def __init__(self, headers, fxml, fxml_out, blacklist=None):
        assert isinstance(headers, (list, tuple, set,))
        assert len(headers) > 0

        self.fxml = fxml
        self.blacklist = blacklist

        self.localized_templates = set()

        self.tree = ET.parse(fxml)
        self.root = self.tree.getroot()

        self.header_ids = []
        self._prepare(headers)

        self._iterate_and_mark()

        self._rebuild_xml()
        self.tree.write(fxml_out)

    @staticmethod
    def load(inf):
        pass

    @staticmethod
    def save(outf):
        pass

    @staticmethod
    def clear():
        pass

    def _prepare(self, headers):
        for header in headers:
            fnode = get_file_node(self.root, header)
            fnode.reserved = True

            self.header_ids.append(fnode.attrib["id"])

    def _rebuild_xml(self):
        toplevel_ids = []

        new_root = ET.Element(self.root.tag, self.root.attrib)
        for node in self.root:
            try:
                if node.reserved:
                    copy = ET.SubElement(new_root, node.tag, node.attrib)
                    toplevel_ids.append(node.attrib["id"])

                    for subnode in node:
                        ET.SubElement(copy, subnode.tag, subnode.attrib)
            except AttributeError, e:
                print(node.tag, node.attrib)
                raise e

        self.tree._setroot(new_root)
        self.root = new_root

        self._strip_unused_namespaces(toplevel_ids)

        for node in self.root.findall(".//*[@location]"):
            node.attrib.pop("location", None)
            node.attrib.pop("line", None)
            node.attrib.pop("mangled", None)

    def _iterate_and_mark(self):
        for header_id in self.header_ids:
            self.curr_file_id = header_id

            self.recompress = True
            while self.recompress:
                self.recompress = False

                for node in self.root:
                    if not hasattr(node, "reserved") or not node.reserved:
                        if node.attrib.get("file") == self.curr_file_id:
                            node.reserved = True

                            if "returns" in node.attrib or "Constructor" == node.tag:
                                self._reserve_args_and_retval_types(node)
                            elif node.tag in ("Class", "Struct",):
                                self._reserve_bases(node)

                                if '<' in node.attrib["name"]:
                                    self._localize_template_class(node)
                            elif node.tag in ("Variable", "Field",):
                                self._do_reserve_type_nodes((node,))
                        else:
                            node.reserved = node.tag in ("Namespace",)

    def _is_local(self, file_id):
        return file_id in self.header_ids

    def _try_reserve_nonlocal_node(self, node):
        if not hasattr(node, "reserved") or not node.reserved:
            if not self._is_local(node.attrib.get("file")):
                node.reserved = True

    def _reserve_args_and_retval_types(self, mnode):
        args_and_retval = []

        for arg in mnode.iter("Argument"):
            args_and_retval.append(arg)

        if "returns" in mnode.attrib:
            retval = self.root.find("./*[@id='%s']" % mnode.attrib["returns"])
            args_and_retval.append(retval)

        self._do_reserve_type_nodes(args_and_retval)
    
    def _do_reserve_type_nodes(self, nodes):
        for node in nodes:
            while True:
                local = self._is_local(node.attrib.get("file"))
                if not local:
                    node.reserved = True

                self._reserve_type_contexts(node)

                type_id = node.attrib.get("type")
                if not type_id:
                    if node.tag in ("Class", "Struct",):
                        if '<' in node.attrib["name"]:
                            self._localize_template_class(node)
                    elif node.tag == "FunctionType":
                        self._reserve_args_and_retval_types(node)

                    break

                node = self.root.find("./*[@id='%s']" % type_id)

    def _reserve_type_contexts(self, node):
        ctx_node_id = node.attrib.get("context", None)

        while ctx_node_id:
            ctx_node = self.root.find("./*[@id='%s']" % ctx_node_id)
            self._try_reserve_nonlocal_node(ctx_node)

            ctx_node_id = ctx_node.attrib.get("context", None)

    def _reserve_bases(self, cls_node):
        if "bases" in cls_node.attrib:
            del cls_node.attrib["bases"]

        depleted_bases = []

        for base in cls_node.findall("Base"):
            base_node = self.root.find("./*[@id='%s']" % base.attrib["type"])

            if self.blacklist and self.blacklist.base(base_node.attrib["demangled"]):
                depleted_bases.append(base)
                continue

            if not self._is_local(base_node.attrib.get("file")):
                base_node.reserved = True

            if '<' in base_node.attrib["name"]:
                self._localize_template_class(base_node)

        for node in depleted_bases:
            cls_node.remove(node)

    def _strip_unused_namespaces(self, ids):
        depleted = []

        for ns in self.root.iter("Namespace"):
            if ns.attrib.get("name") == "::":
                continue

            reserve = False

            for member in ns.attrib.get("members", "").split(' '):
                if member in ids:
                    reserve = True
                    break

            if not reserve:
                depleted.append(ns)

        for node in depleted:
            self.root.remove(node)

    def _localize_template_class(self, cls_node):
        full_name = cls_node.attrib["demangled"]
        if full_name in self.localized_templates:
            return

        cls_node.set("file", self.curr_file_id)
        cls_node.reserved = False  # reassign in the next compress loop

        for node in self.root.findall("./*[@context='%s']" % cls_node.attrib["id"]):
            if "file" in node.attrib:
                node.set("file", self.curr_file_id)

        self.localized_templates.add(full_name)
        self.recompress = True


def _test_blacklist():
    import re

    class MyBlackList(Compressor.BlackList):

        _base_patters = [
            re.compile(r"std::_Vector_base<.+, std::allocator<.+> >"),
        ]

        _bases = []

        def base(self, full_name):
            for pattern in self._base_patters:
                if pattern.match(full_name):
                    return True

            return full_name in self._bases


    c = Compressor((r"C:\Users\wxn\Desktop\X.h", r"C:\Users\wxn\Desktop\Y.h",),
                    r"C:\Users\wxn\Desktop\X.xml",
                    r"C:\Users\wxn\Desktop\XX.xml",
                    blacklist=MyBlackList())

    print(c.localized_templates)


if __name__ == "__main__":
    import time

    t1 = time.time()
    c = Compressor((r"filedlg.hpp",
                    r"D:\Work\CppLibs\wxMSW\include\wx/msw/filedlg.h",),
                    r"Tests/FILEDLG.xml", r"Tests/FILEDLG_x.xml")

    t2 = time.time()
    print("Time used: %gs" % (t2 - t1))
