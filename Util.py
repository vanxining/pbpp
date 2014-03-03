__author__ = 'wxn'


def context_of(node, root):
    namespaces = []
    node_id = node.attrib["context"]

    while node_id:
        node = root.find(".//*[@id='%s']" % node_id)
        ns = node.attrib["name"]
        if ns != "::":
            namespaces.insert(0, ns)
            node_id = node.attrib.get("context", None)
        else:
            break

    return "::".join(namespaces)


def full_name_of(node, root):
    context = context_of(node, root)
    if context:
        return context + "::" + node.attrib["name"]
    else:
        return node.attrib["name"]


def _test_context(root):
    for node_id in ("_33",):
        print context_of(root.find(".//*[@id='%s']" % node_id), root)


def _test_full_name(root):
    for node_id in ("_4",):
        print full_name_of(root.find(".//*[@id='%s']" % node_id), root)


if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    r = ET.parse("wx.xml").getroot()

    _test_full_name(r)
    _test_context(r)
