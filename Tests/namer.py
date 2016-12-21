from .. import Module


class TestNamer(Module.PythonNamer):
    def package(self):
        return "Test"
