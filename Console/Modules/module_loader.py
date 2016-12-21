import importlib
import os


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
