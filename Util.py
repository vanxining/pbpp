import importlib
import logging
import os
import time


def smart_write(path, content, log=True):
    if not os.path.exists(path) or open(path).read() != content:
        with open(path, "w") as outf:
            outf.write(content)

        if log:
            logging.info("Written `%s`.", os.path.realpath(path))

        return True

    return False


def smart_copy(src, dst, log=True):
    content = open(src).read()

    if smart_write(dst, content, log=False):
        if log:
            logging.info("Copied to `%s`.", os.path.realpath(dst))


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
            fmt = 'XML node attribute `name` not found: tag="%s", attrib=%s'
            logging.exception(fmt, node.tag, node.attrib)

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


# noinspection PyProtectedMember
def load2(name):
    reloaded = False

    mod = importlib.import_module(name)
    path = mod.__file__

    pyc = False
    if path.endswith(".pyc"):
        path = path[:-1]
        pyc = True

    mtime = os.path.getmtime(path)
    if hasattr(mod, "_pbpp_loadtime") and mtime > mod._pbpp_loadtime:
        if pyc and os.path.exists(mod.__file__):
            os.remove(mod.__file__)

        mod = reload(mod)
        reloaded = True

    mod._pbpp_loadtime = mtime

    return mod, reloaded


def load(name):
    return load2(name)[0]


class ElapsedTime(object):
    def __init__(self, fmt=""):
        self.fmt = fmt or "Time elapsed: %gs"
        self.time_begin = 0.0

    def __enter__(self):
        self.time_begin = time.time()

    def __exit__(self, exc_type, exc_value, tb):
        logging.info(self.fmt, time.time() - self.time_begin)
