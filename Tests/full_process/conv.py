from ... import Converters


class WstringConv(Converters.Converter):
    def match(self, cpp_type):
        if cpp_type.intrinsic_type() == "wstring":
            if not cpp_type.is_trivial():
                if cpp_type.is_const() or not cpp_type.has_decorators():
                    return True

        return False

    def specifier(self, cpp_type):
        return "u"

    def args_parsing_declare_vars(self, cpp_type, var_name, defv=None):
        init_expr = "nullptr"
        if defv is not None:
            init_expr = "(const wchar_t *) " + defv

        return "const wchar_t *%s = %s;" % (var_name, init_expr)

    def args_parsing_interim_vars(self, cpp_type, arg_name, pytype):
        return "&" + arg_name

    def args_parsing_extracting_code(self, cpp_type, arg_name, defv, error_return, namer):
        return ""

    def args_parsing_require_error_handling(self, cpp_type):
        return False

    def negative_checker(self, cpp_type, py_var_name):
        return "!PyUnicode_Check(%s)" % py_var_name

    def extracting_code(self, cpp_type, var_name, py_var_name, error_return, namer):
        var = "(const wchar_t *) PyUnicode_AsUnicode(%s)" % py_var_name
        return cpp_type.declare_var(var_name, var)

    def value_building_interim_var(self, arg_name):
        return arg_name + ".c_str()"

    def build(self, cpp_type, var_name, py_var_name, namer, raii):
        common_part = "PyUnicode_FromWideChar({1}.c_str(), {1}.length())"
        boilerplate = "pbpp::PyObjectPtr {{0}}({});" if raii else "PyObject *{{0}} = {};"

        return boilerplate.format(common_part).format(py_var_name, var_name)
