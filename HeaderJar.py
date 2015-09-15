__author__ = 'wxn'


class HeaderJar:
    def __init__(self):
        self.exts = (".h", ".hpp", ".hxx", ".h++", ".hcc", ".hh")
        self.headers = []

    def add_headers(self, headers):
        assert isinstance(headers, (list, tuple, set,))

        for header in headers:
            assert len(header) > 0

            if header[0] in '<"' and header[-1] in '">':
                decl = "#include " + header
                if decl not in self.headers:
                    self.headers.append(decl)
            else:
                pos = header.rfind(".")
                if pos == -1 or header[pos:].lower() not in self.exts:
                    header += ".h"

                decl = '#include "%s"' % header
                if decl not in self.headers:
                    self.headers.append(decl)

    def remove_header(self, header_decl):
        try:
            self.headers.remove(header_decl)
        except ValueError, e:
            pass

    def concat(self):
        return '\n'.join(self.headers)
