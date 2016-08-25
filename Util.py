
import os
import importlib


def smart_write(path, content):
    if not os.path.exists(path) or open(path).read() != content:
        with open(path, "w") as outf:
            outf.write(content)

        print("Written `%s`." % os.path.realpath(path))


def split_namespaces(namespaces):
    splitted = []
    depth = 0
    ns = []

    while len(namespaces) > 0:
        if namespaces[-1] == '>':
            depth += 1
        elif namespaces[-1] == '<':
            depth -= 1
        elif namespaces.endswith("::"):
            if depth == 0:
                namespaces = namespaces[:-2]

                ns.reverse()
                splitted.append("".join(ns))
                ns = []

                continue

        ns.append(namespaces[-1])
        namespaces = namespaces[:-1]

    if len(ns) > 0:
        ns.reverse()
        splitted.append("".join(ns))

    splitted.reverse()
    return splitted


def context_of(node, root):
    namespaces = []
    node_id = node.attrib["context"]

    while node_id:
        node = root.find(".//*[@id='%s']" % node_id)
        try:
            ns = node.attrib["name"]
        except AttributeError, e:
            print("!! Lacks `%s` !!" % node_id)
            raise e

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


def load2(name):
    reloaded = False

    mod = importlib.import_module(name)
    path = mod.__file__

    pyc = False
    if path.endswith(".pyc"):
        path = path[:-1]
        pyc = True

    mtime = os.path.getmtime(path)
    if hasattr(mod, "_loadtime") and mtime > mod._loadtime:
        if pyc and os.path.exists(mod.__file__):
            os.remove(mod.__file__)
        
        mod = reload(mod)
        reloaded = True
    
    mod._loadtime = mtime

    return mod, reloaded


def load(name):
    return load2(name)[0]


def _test_context(root):
    for node_id in ("_33",):
        print context_of(root.find(".//*[@id='%s']" % node_id), root)


def _test_full_name(root):
    for node_id in ("_4",):
        print full_name_of(root.find(".//*[@id='%s']" % node_id), root)


if __name__ == "__main__":
    print split_namespaces("std::vector<int, std::allocator<int> >")
    print split_namespaces("std::vector<std::allocator<std::size_t>, std::allocator<int> >::const_iterator")

    import xml.etree.ElementTree as ET
    r = ET.parse("wx.xml").getroot()

    _test_full_name(r)
    _test_context(r)