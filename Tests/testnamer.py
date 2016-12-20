
from ..Module import PythonNamer


class TestNamer(PythonNamer):
    @staticmethod
    def package():
        return "Test"

    def _to_python(self, name):
        if '<' in name:
            # Remove STL containers' allocator template argument.
            for container in ("vector", "list", "set", "deque",):
                if name.startswith(container):
                    name = name[:name.index(',')] + '>'
                    break

            name = PythonNamer.normalize_template(name)

        return name
