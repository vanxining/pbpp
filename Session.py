
_header_jars = []


def begin(hdr_jar):
    _header_jars.append(hdr_jar)

def end():
    global _header_jars
    _header_jars.pop()

def header_jar():
    return _header_jars[-1]


ignored_namespaces = set()
ignored_fields = set()

ignored_classes = set()
ignored_bases = set()

ignored_methods = set()
ignored_free_functions = set()

dummy_classes = set()


def clear_ignored_symbols_registry():
    global ignored_namespaces
    global ignored_classes, ignored_bases, dummy_classes
    global ignored_methods, ignored_free_functions
    global ignored_fields

    ignored_namespaces = set()
    ignored_fields = set()
    ignored_classes = set()
    ignored_bases = set()
    ignored_methods = set()
    ignored_free_functions = set()

    dummy_classes = set()


def print_ignored_symbols_registry():
    print("")
    print("---------------------------------------------")

    _print(ignored_namespaces, "ignored_namespaces")
    _print(ignored_fields, "ignored_fields")
    _print(ignored_classes, "ignored_classes")
    _print(ignored_bases, "ignored_bases")
    _print(ignored_methods, "ignored_methods")
    _print(ignored_free_functions, "ignored_free_functions")
    _print(dummy_classes, "dummy_classes")


def _print(container, var_name):
    if len(container) == 0:
        return

    print("")
    print("[%s]" % var_name)

    for item in container:
        print("  " + item)
