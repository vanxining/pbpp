

class FptrManager:
    def __init__(self):
        self.fptrs = {}

    def try_add(self, ctype):
        if ctype.is_function_pointer():
            self.fptrs[ctype.decl()] = ctype

    def empty(self):
        return len(self.fptrs) == 0

    def generate(self, block):
        for fp in self.fptrs.values():
            block.write_code(fp.typedef(fp.decl()))
