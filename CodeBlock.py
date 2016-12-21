class CodeBlock(object):
    def __init__(self, init_indent_cnt=0):
        self.lines = []
        self.indent_cnt = init_indent_cnt

    def empty(self):
        return len(self.lines) == 0

    def size(self):
        return len(self.lines)

    def write_code(self, code, temp_indent=None):
        assert isinstance(code, str)

        if code:
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

    def write_error_check(self, chk, handler, otherwise=None, handler_label=None):
        self._do_write_error_check("if (%s)" % chk, handler, handler_label)

        if otherwise is not None and len(otherwise) > 0:
            self._do_write_error_check("else", otherwise, None)

    def _do_write_error_check(self, preamble, handler, handler_label):
        self.write_code(preamble + " {")
        self.indent()

        if handler_label:
            self.lines.append(handler_label + ':')

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
        if len(self.lines) > 0:
            content = "\n".join(self.lines)
            self.clear()

            return content
        else:
            return ""

    def clear(self):
        self.lines = []


class Scope(object):
    def __init__(self, block):
        self.block = block

    def __enter__(self):
        self.block.write_code("do {")
        self.block.indent()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.unindent()
        self.block.write_code("} while (0);")


class BracketThis(object):
    def __init__(self, block, preamble=None, postscript=None):
        self.preamble = preamble or ""
        self.postscript = postscript or ""
        self.block = block

    def __enter__(self):
        if self.preamble or len(self.block.lines) == 0:
            self.block.write_code(self.preamble + "{")
        else:
            self.block.lines[-1] += " {"

        self.block.indent()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.block.unindent()

        if self.block.lines[-1] and self.block.lines[-1][-1] == '{':
            self.block.lines[-1] += '}'
        else:
            self.block.write_code('}')

        self.block.lines[-1] += self.postscript
        self.block.append_blank_line()
