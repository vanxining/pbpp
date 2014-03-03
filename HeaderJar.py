__author__ = 'wxn'


class HeaderJar:
    def __init__(self):
        self.headers = []

    def add_headers(self, headers):
        assert isinstance(headers, (list, tuple,))

        exts = (".h", ".hpp", ".hxx", ".h++", ".hcc", ".hh")

        for header in headers:
            if header[0] in '<"' and header[-1] in '">':
                decl = "#include " + header
                if decl not in self.headers:
                    self.headers.append(decl)
            else:
                pos = header.rfind(".")
                if pos == -1 or header[pos:].lower() not in exts:
                    header += ".h"

                decl = '#include "%s"' % header
                if decl not in self.headers:
                    self.headers.append(decl)

    def concat(self):
        return '\n'.join(self.headers)