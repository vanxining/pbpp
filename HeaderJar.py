__author__ = 'wxn'


class HeaderJar:
    def __init__(self):
        self.exts = (".h", ".hpp", ".hxx", ".h++", ".hcc", ".hh")
        self.headers = []
        self.globals = []

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

    def add_global(self, global_decl):
        if global_decl not in self.globals:
            self.globals.append(global_decl)

    def remove_global(self, global_decl):
        try:
            self.globals.remove(global_decl)
        except ValueError, e:
            pass

    def concat_sorted(self):
        ret = '\n'.join(sorted(self.headers))

        if len(self.globals) > 0:
            ret += "\n\n" + '\n'.join(sorted(self.globals))

        return ret
