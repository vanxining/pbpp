__author__ = 'wxn'


class CodeBlock:
    def __init__(self, init_indent_cnt=0):
        self.lines = []
        self.indent_cnt = init_indent_cnt

        self.writeln = self.write_code

    def write_code(self, code, temp_indent=None):
        assert isinstance(code, str)
        self.write_lines(code.split('\n'), temp_indent)

    def write_lines(self, lines, temp_indent=None):
        assert isinstance(lines, (list, tuple, set))

        if len(lines) > 0:
            indent = self.indent_cnt
            if temp_indent is not None:
                indent = temp_indent

            for line in lines:
                if line.startswith("<!"):
                    line = line[2:].rstrip()
                elif line.startswith(">>>"):
                    indent += 4 * (line.count('>') / 3)
                    continue
                elif line.startswith("<<<"):
                    indent -= 4 * (line.count('<') / 3)
                    continue
                else:
                    line = ' ' * indent + line.rstrip()

                self.lines.append(line)

    def write_error_check(self, chk, handler, otherwise=None):
        self._do_write_error_check("if (%s)" % chk, handler)

        if otherwise is not None and len(otherwise) > 0:
            self._do_write_error_check("else", otherwise)

    def _do_write_error_check(self, preamble, handler):
        self.write_code(preamble + " {")
        self.indent()
        self.write_code(handler)
        self.unindent()
        self.write_code('}')

    def append_blank_line(self):
        self.lines.append("")

    def indent(self):
        self.indent_cnt += 4

    def unindent(self):
        self.indent_cnt -= 4

    def flush(self):
        content = "\n".join(self.lines)
        self.clear()

        return content

    def clear(self):
        self.lines = []


class Scope:
    def __init__(self, block):
        self.block = block

    def __enter__(self):
        self.block.write_code("do {")
        self.block.indent()
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.unindent()
        self.block.write_code("} while (0);")


class BracketThis:
    def __init__(self, block, preamble=None, postscript=None):
        self.preamble = preamble or ""
        self.postscript = postscript or ""
        self.block = block

    def __enter__(self):
        self.block.write_code(self.preamble + "{")
        self.block.indent()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.unindent()
        self.block.write_code("}" + self.postscript)
        self.block.append_blank_line()
