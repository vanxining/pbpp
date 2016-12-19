
from ..Module import PythonNamer


class MyNamer(PythonNamer):
    @staticmethod
    def package():
        return "Raw"

    def _to_python(self, name):
        if '<' in name:
            for container in ("vector", "list", "set", "deque",):
                if name.startswith(container):
                    name = name[:name.index(',')] + '>'
                    break

            name = PythonNamer.normalize_template(name)

        return name
