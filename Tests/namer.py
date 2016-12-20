
from .. import Module


class TestNamer(Module.PythonNamer):
    @staticmethod
    def package():
        return "Test"
