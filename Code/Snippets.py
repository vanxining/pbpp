
module_creator_header = '''
extern "C" PyObject *%(FUNC_NAME)s(PyObject *parent) {
    PyObject *m = CreateModule("%(MNAME_FULL)s");
    if (!m) {
        return nullptr;
    }

    if (parent) {
        Py_INCREF(m);
        PyModule_AddObject(parent, (char *) "%(MNAME)s", m);
    }
'''

register_global_constants_sig = "static void __Globals(PyObject *m)"
module_register_enums_sig = 'static void __Enums(PyObject *m)'

# Class basis

offset_base_ptr_sig = "static void *FixBasePtr(void *cxx_obj, PyTypeObject *base_type)"

pyobj_decl = '''typedef struct {
    PyObject_HEAD
    %%(WRAPT)s *cxx_obj;
    FpOffsetBase fp_offset_base;
    pbpp_flag_t flags : 8;
} %%(PYOBJ_NAME)s;

%s;
extern PyTypeObject %%(PYTYPE_NAME)s;
''' % offset_base_ptr_sig


# Constructor and destructor

ctor_sig = '''static int %(CTOR_NAME)s(%(PYOBJ_NAME)s *self, PyObject *args, PyObject *kwargs)'''

ctor_error_accessibility = '''PyErr_SetString(PyExc_TypeError, "Class `%s` has no accessible constructors.");
PyErr_Print();
return -1;'''

ctor_chk_abstract = '''if (Py_TYPE(self) == &%(PYTYPE_NAME)s) {
    PyErr_SetString(PyExc_TypeError, "Abstract class `%(CLS_NAME)s` cannot be instantiated.");
    PyErr_Print();
    return -1;
}
'''

constructing = '''PBPP_BEGIN_ALLOW_THREADS
auto cxx_obj = new %s(%%s);
PBPP_END_ALLOW_THREADS

self->cxx_obj = cxx_obj;'''

ctor_actions_more = '''self->fp_offset_base = FixBasePtr;
self->flags = %s;'''

ctor_incref = "Py_INCREF(self);"

# Exceptions may occur in ctor, so cxx_obj may be null
dealloc = '''static void %(DTOR_NAME)s(%(PYOBJ_NAME)s *self) {
    if (!(self->flags & pbpp::LifeTime::BORROWED)) {
        auto cxx_obj = self->cxx_obj;
        if (cxx_obj) {
            self->cxx_obj = nullptr;

            if (self->flags & pbpp::LifeTime::PYTHON) {
                PBPP_BEGIN_ALLOW_THREADS
                delete cxx_obj;
                cxx_obj = nullptr;
                PBPP_END_ALLOW_THREADS
            }
        }
    }

    Py_TYPE(self)->tp_free(self);
}'''

dealloc_trivial = '''static void %(DTOR_NAME)s(%(PYOBJ_NAME)s *self) {
    self->cxx_obj = nullptr;
    Py_TYPE(self)->tp_free(self);
}'''


# Wrapper class

wrapper_dtor = '''~%s() {
    if (self) {
        auto _self = self;
        self->cxx_obj = nullptr;
        self = nullptr;

        PBPP_NEW_THREAD_BLOCKER
        Py_DECREF(_self);
    }
}
'''


# Class fields

field_getter_sig = "static PyObject *%s(%s *self, void *PBPP_UNUSED(py_closure))"
field_setter_sig = "static int %s(%s *self, PyObject *py_value, void *PBPP_UNUSED(py_closure))"

field_table_begin = "static PyGetSetDef __getsets[] = {"
field_table_entry = '    { (char *) "%(NAME)s", (getter) %(GETTER)s, (setter) %(SETTER)s, nullptr, nullptr },'
field_table_end = '''    {  nullptr, nullptr, nullptr, nullptr, nullptr }
};
'''


# Class inheritance

TestSubclassAndOffset = "auto cxx_obj = (%(WRAPT)s *) self->fp_offset_base(self->cxx_obj, &%(MY_PYTYPE)s);"

offset_base_ptr_simple = offset_base_ptr_sig + ''' {
    return cxx_obj;
}'''

offset_base_ptr_header = offset_base_ptr_sig + ''' {
    if (base_type == &%s) {
        return cxx_obj;
    }

    auto p = (unsigned long) cxx_obj;
'''

offset_base_ptr_item = '''if (base_type == &%(BASE_PYTYPE)s) {
    p += (unsigned long)(((%(BASE)s *)((%(WRAPT)s *) 100))) - 100;
    return (void *) p;
}'''

register_bases_sig = 'static void __Bases()'
register_enums_sig = 'static void __Enums()'

protected_enum_register = '''struct EnumRegister : public %s {
    static void Register()'''

base_tuple_item = '''Py_INCREF((PyObject *) &%(BASE_TYPE)s);
PyTuple_SET_ITEM(%(DERIVED_TYPE)s.tp_bases, %(INDEX)d, (PyObject *) &%(BASE_TYPE)s);'''

register_class = '''extern "C" void %(REGISTER)s(PyObject *m) {
    __Bases();

    if (PyType_Ready(&%(PYTYPE)s) == 0) {
        %(ACTION)s
        __M::__Enums();
    }
}
'''

register_as_toplevel = (
    'PyModule_AddObject(m, (char *) "%(PYSIDE_SHORT)s", (PyObject *) &%(PYTYPE)s);'
)

register_as_nested = (
    'PyDict_SetItemString(%(PYTYPE_NESTER)s.tp_dict, (char *) "%(PYSIDE_SHORT)s", (PyObject *) &%(PYTYPE)s);'
)

register_module_enum_values = '''
EnumValue *val = __values;
while (val->name) {
    PyModule_AddIntConstant(m, (char *) val->name, val->value);
    val++;
}'''

register_class_enum_values = '''
RegisterEnumValues(__values, %s.tp_dict);'''


# Build/parse arguments and retval

PyArg_ParseTupleAndKeywords = (
    'PyArg_ParseTupleAndKeywords(%(TUPLE)s, %(KW_TUPLE)s, %(FORMAT)s, (char **) %(KW_ARRAY)s, %(ARGS)s)'
)

PyArg_ParseTuple = (
    'PyArg_ParseTuple(%(TUPLE)s, %(FORMAT)s, %(ARGS)s)'
)

Py_BuildValue = (
    'Py_BuildValue((char *) %(FORMAT)s, %(BUILDER)s(%(CVAL)s))'
)

PyCapsule_New = (
    'PyObject *%(PY_VAR_NAME)s = (%(VAR)s) ? PyCapsule_New((void *) %(VAR)s, "%(TYPE_STR)s", nullptr) : Py_None;'
)

PyCapsule_New_RAII = (
    'PyObjectPtr %(PY_VAR_NAME)s((%(VAR)s) ? PyCapsule_New((void *) %(VAR)s, "%(TYPE_STR)s", nullptr) : Py_None);'
)

PyCapsule_GetPointer = '''if (py_%(VAR_NAME)s) {
    %(VAR_NAME)s = (%(CPP_PTR_TYPE)s) PyCapsule_GetPointer(py_%(VAR_NAME)s, "%(CAP_NAME)s");
}
'''

capsule_ensure_reference = '''if (!PyCapsule_IsValid(py_%(VAR_NAME)s, "%(CAP_NAME)s")) {
    %(ERROR_RETURN)s
}'''

to_built_in_type = "%(CTYPE)s %(VAL)s = static_cast<%(CTYPE)s>(%(EXTRACTOR)s(%(PYOBJ)s));"

external_type_real_ptr = (
    '*((%(CLASS)s **) (((unsigned long)(PyObject *) %(PYOBJ_PTR)s) + sizeof(PyObject)))'
)

extract_pointer = '''if (PyObject_TypeCheck(py_%(VAR_NAME)s, &%(PYTYPE)s)) {
    %(VAR_NAME)s = %(EXTRACTING_CODE)s;
}
else {
    PyErr_Format(PyExc_TypeError, "[%%s:%%d<%%s>] Pointer of type `%(POINTER_TYPE)s` is required.", __FILE__, __LINE__, __FUNCTION__);
>>>
%(ERROR_HANDLER)s
<<<
}'''

no_defv_error_check = '''else {
>>>
%s
<<<
}'''

check_and_extract_as_bool = '''if (py_%(VAR_NAME)s) {
    %(VAR_NAME)s = (PyObject_IsTrue(py_%(VAR_NAME)s) == 1);
}'''

single_var_extractor = '''if (%(NEGATIVE_CHECKER)s) {
    PyErr_Format(PyExc_TypeError, "[%%s:%%d<%%s>] Object of type `%(VAR_TYPE)s` is required.", __FILE__, __LINE__, __FUNCTION__);
>>>
%(ERROR_RETURN)s
<<<
}
%(EXTRACTING_CODE)s'''

extract_builtin_type = "%(VAR_TYPE)s %(VAR_NAME)s = %(CAST_ENUM)s%(EXTRACTOR)s(%(PY_VAR_NAME)s);"

extract_sequence = '''Py_ssize_t __len = PySequence_Length(%(PY_VAR_NAME)s);
for (Py_ssize_t i = 0; i < __len; i++) {
    PyObject *py_item = PySequence_ITEM(%(PY_VAR_NAME)s, i);
>>>
%(ITEM_EXTRACTING_CODE)s
<<<
}'''

extract_container = '''auto __%(VAR_NAME)s_item_extractor = [](PyObject *py_item, %(ITEM_TYPE)s%(SPACE)s&item) {
>>>
%(EXTRACTOR)s
<<<
};
auto __%(VAR_NAME)s_item_builder = [](Python::const_ref<%(ITEM_TYPE)s>::type item, PyObject *&py_item) {
>>>
%(BUILDER)s
<<<
};
Python::List<%(CONTAINER_TYPE)s, decltype(__%(VAR_NAME)s_item_extractor), decltype(__%(VAR_NAME)s_item_builder)>
    %(VAR_NAME)s(%(PY_VAR_NAME)s, Python::%(REFERENCE_TYPE)s, __%(VAR_NAME)s_item_extractor, __%(VAR_NAME)s_item_builder);
%(SET_DEFAULT_VALUE)sif (!%(VAR_NAME)s.ConvertFromPython()) {
>>>
%(ERROR_RETURN)s
<<<
}'''

_build_list_common = '''
for (%(SIZE_TYPE)s i = 0, cnt = %(COUNT)s; i < cnt; i++) {
>>>
%(ITEM_BUILDING_CODE)s
<<<
    PyList_SetItem(%(PY_VAR_NAME)s, i, py_item);
}'''

build_list = "PyObject *%(PY_VAR_NAME)s = PyList_New(%(COUNT)s);" + _build_list_common
build_list_raii = "PyObjectPtr %(PY_VAR_NAME)s(PyList_New(%(COUNT)s));" + _build_list_common

simple_extract_dict = '''PyObject *py_dict_key, *py_dict_value;
Py_ssize_t __pos = 0;
while (PyDict_Next(%(PY_VAR_NAME)s, &__pos, &py_dict_key, &py_dict_value)) {
>>>
%(KV_EXTRACTING_CODE)s
<<<
    %(VAR_NAME)s[key] = value;
}'''

extract_dict = '''auto __%(VAR_NAME)s_key_extractor = [](PyObject *py_key, %(KEY_TYPE)s%(K_SPACE)s&key) {
>>>
%(KEY_EXTRACTOR)s
<<<
};
auto __%(VAR_NAME)s_key_builder = [](Python::const_ref<%(KEY_TYPE)s>::type key, PyObject *&py_key) {
>>>
%(KEY_BUILDER)s
<<<
};
auto __%(VAR_NAME)s_val_extractor = [](PyObject *py_val, %(VALUE_TYPE)s%(V_SPACE)s&val) {
>>>
%(VALUE_EXTRACTOR)s
<<<
};
auto __%(VAR_NAME)s_val_builder = [](Python::const_ref<%(VALUE_TYPE)s>::type val, PyObject *&py_val) {
>>>
%(VALUE_BUILDER)s
<<<
};
Python::Dict<%(CONTAINER_TYPE)s,
             decltype(__%(VAR_NAME)s_key_extractor),
             decltype(__%(VAR_NAME)s_key_builder),
             decltype(__%(VAR_NAME)s_val_extractor),
             decltype(__%(VAR_NAME)s_val_builder)>
    %(VAR_NAME)s(%(PY_VAR_NAME)s, Python::%(REFERENCE_TYPE)s,
        __%(VAR_NAME)s_key_extractor,
        __%(VAR_NAME)s_key_builder,
        __%(VAR_NAME)s_val_extractor,
        __%(VAR_NAME)s_val_builder);
%(SET_DEFAULT_VALUE)sif (!%(VAR_NAME)s.ConvertFromPython()) {
>>>
%(ERROR_RETURN)s
<<<
}'''

_build_dict_common = '''
for (auto &kv : %(VAR_NAME)s) {
>>>
%(KEY_BUILDING_CODE)s
%(VAL_BUILDING_CODE)s
<<<
    PyDict_SetItem(%(PY_VAR_NAME)s, py_dict_key, py_dict_value);
    Py_DECREF(py_dict_key);
    Py_DECREF(py_dict_value);
}'''

build_dict = "PyObject *%(PY_VAR_NAME)s = PyDict_New();" + _build_dict_common
build_dict_raii = "PyObjectPtr %(PY_VAR_NAME)s(PyDict_New());" + _build_dict_common


# Borrower & copyer

# For classes without wrappers
borrower = '''PyObject *%(BORROWER)s(const %(CLASS)s &from) {
    %(PYOBJ_STRUCT)s *pyobj = nullptr;
>>>
%(QUICK_BORROW)s
<<<
    pyobj = PyObject_New(%(PYOBJ_STRUCT)s, &%(PYTYPE)s);
    pyobj->cxx_obj = (%(CLASS)s *) &from;
    pyobj->fp_offset_base = FixBasePtr;
    pyobj->flags = pbpp::LifeTime::CXX;

    return (PyObject *) pyobj;
}
'''

# For classes with wrappers
borrower2 = '''PyObject *%(BORROWER)s(const %(CLASS)s &from) {
    %(PYOBJ_STRUCT)s *pyobj = nullptr;
>>>
%(QUICK_BORROW)s
<<<
    if (typeid(from).name() == typeid(%(WRAPT)s).name()) {
        pyobj = ((%(WRAPT)s &) from).self;
        Py_INCREF(pyobj);
    }
    else {
        pyobj = PyObject_New(%(PYOBJ_STRUCT)s, &%(PYTYPE)s);
        pyobj->cxx_obj = (%(WRAPT)s *) &from;
        pyobj->fp_offset_base = FixBasePtr;
        pyobj->flags = pbpp::LifeTime::BORROWED;
    }

    return (PyObject *) pyobj;
}
'''

borrow_from_python_aware_class = '''pyobj = (%(PYOBJ_STRUCT)s *) from.%(SELF_GETTER)s;
if (pyobj) {
    return (PyObject *) pyobj;
}
'''

borrow_from_ref = '''PyObject *%(BORROWER)s(const %(CLASS)s &from);
PyObject *%(PY_VAR_NAME)s = %(BORROWER)s(%(REF)s);'''

borrow_from_ref_raii = '''PyObject *%(BORROWER)s(const %(CLASS)s &from);
PyObjectPtr %(PY_VAR_NAME)s(%(BORROWER)s(%(REF)s));'''

borrow_from_ptr = '''PyObject *%(PY_VAR_NAME)s_raw;
if (%(PTR)s) {
    PyObject *%(BORROWER)s(const %(CLASS)s &from);
    %(PY_VAR_NAME)s_raw = %(BORROWER)s(%(REF)s);
}
else {
    Py_INCREF(Py_None);
    %(PY_VAR_NAME)s_raw = Py_None;
}'''

ensure_not_null = '''if (!retval) {
    Py_RETURN_NONE;
}
'''

init_helper_self = '''pyobj->cxx_obj->self = pyobj;
    '''

copyer = '''PyObject *%(COPYER)s(const %(CLASS)s &from, pbpp_flag_t flags) {
    PBPP_BEGIN_ALLOW_THREADS
    %(WRAPT)s *cxx_obj = new %(WRAPT)s(*((const %(WRAPT)s *) &from));
    PBPP_END_ALLOW_THREADS

    %(PYOBJ_STRUCT)s *pyobj = PyObject_New(%(PYOBJ_STRUCT)s, &%(PYTYPE)s);
    pyobj->cxx_obj = cxx_obj;
    %(INIT_HELPER_SELF)spyobj->fp_offset_base = FixBasePtr;
    pyobj->flags = flags;

    return (PyObject *) pyobj;
}
'''

copy = '''PyObject *%(COPYER)s(const %(CLASS)s &from, pbpp_flag_t flags);
PyObject *%(PY_VAR_NAME)s = %(COPYER)s(%(VAR)s, pbpp::LifeTime::PYTHON);'''

copy_raii = '''PyObject *%(COPYER)s(const %(CLASS)s &from, pbpp_flag_t flags);
PyObjectPtr %(PY_VAR_NAME)s(%(COPYER)s(%(VAR)s, pbpp::LifeTime::PYTHON));'''


# Methods

method_sig = "static PyObject *%(NAME)s(%(PYOBJ_NAME)s *self, PyObject *args, PyObject *kwargs)"
method_sig_no_arg = "static PyObject *%(NAME)s(%(PYOBJ_NAME)s *self)"

ff_sig = "static PyObject *__%(NAME)s(PyObject *PBPP_UNUSED(m), PyObject *args, PyObject *kwargs)"
ff_sig_no_arg = "static PyObject *__%(NAME)s()"

method_table_begin = "static PyMethodDef __methods[] = {"
method_table_end = '''    {  nullptr, nullptr, 0, nullptr }
};
'''

invoke_fx_returning_void = '''PBPP_BEGIN_ALLOW_THREADS
%s%s(%%s);
PBPP_END_ALLOW_THREADS

Py_RETURN_NONE;'''


# Function overload

overloading_exception_cache = '''PyObject *exceptions[%d + 1] = {};
pbpp::ExceptionArrayDestructor exdtor(exceptions);
'''

overloading_label = "__%(FUNC_NAME)s_OVERLOAD_%(INDEX)d"
overloading_cache_exception = "pbpp::CachePythonException(&exceptions[%d]);\n"
overloading_restore_exceptions = "pbpp::RestorePythonExceptions(exceptions, %d);\n\n"


# Virtual function wrapper

throw_cxxexception = 'throw %(EXCEPTION)s("%(RET)s %(SIG)s");'
invoke_def_impl = 'return %(WRAPT)s::%(MNAME)s(%(ARGS)s);'

handle_return_void = '''if (py_vm_retval != Py_None) {
    PyErr_Print();
    throw pbpp::CallPyMethodError("%s");
}'''


def virtual_method_wrapper_header(pure_virtual):
    boilerplate = '''PBPP_NEW_THREAD_BLOCKER

PyObjectPtr py_method(PyObject_GetAttrString((PyObject *) self, (char *) "%%(MNAME)s"));
PyErr_Clear();

if (!py_method || Py_TYPE(py_method) == &PyCFunction_Type ||
     pbpp::GetMethodArgsCount(py_method) != (%%(ARGS_COUNT)d + 1)) {
        py_method.release();
        PBPP_DISABLE_THREAD_BLOCKER
        %s
}

%%(BUILD_ARGS)sPyObjectPtr py_vm_retval(PyObject_CallFunctionObjArgs(py_method, %%(CM_ARGS)s));'''

    if pure_virtual:
        args = "%(EXCEPTION)s", "pbpp::PureVirtualFunctionNotImplemented", 1
        return boilerplate % throw_cxxexception.replace(*args)
    else:
        return boilerplate % invoke_def_impl
