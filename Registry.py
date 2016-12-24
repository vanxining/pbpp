import Class


_registry = {}
_sorted = []


def restore_from_module(m):
    for cls in m.classes.values():
        add_class(cls)

    for subm in m.submodules.values():
        restore_from_module(subm)


def clear():
    global _registry, _sorted
    _registry = {}
    _sorted = []


def get_class(full_name):
    return _registry.get(full_name, None)


def add_class(cls):
    assert isinstance(cls, Class.Class)

    global _registry
    _registry[cls.full_name] = cls


def classes():
    for cls in _registry.values():
        yield cls


class _Class(object):
    def __init__(self, cls):
        assert isinstance(cls, Class.Class)

        self.ref = cls
        self.depends = set(b for b in cls.direct_bases)

        if cls.nester:
            self.depends.add(cls.nester)


def _sort_classes():
    klasses = {cls_name: _Class(_registry[cls_name]) for cls_name in _registry}
    global _sorted
    _sorted = []

    while len(klasses) > 0:
        _do_sort_classes(klasses)


def _do_sort_classes(klasses):
    for cls_name in sorted(klasses.keys()):
        if len(klasses[cls_name].depends) == 0:
            cls = klasses.pop(cls_name)
            _sorted.append(cls.ref)

            for c in klasses.values():
                if cls_name in c.depends:
                    c.depends.remove(cls_name)

            return

    print("")
    print([cls.full_name for cls in _sorted])
    print("")

    for cls in klasses.values():
        print(cls.ref.full_name, cls.depends)

    raise RuntimeError("Unexposed classes as base classes exist.")


def sort_out():
    _sort_classes()

    for cls in _registry.values():
        cls.collect_all_bases()
        cls.collect_virtual_members()


def get_sorted():
    assert len(_sorted) == len(_registry)
    return _sorted
