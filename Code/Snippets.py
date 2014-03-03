
module_creator_header = '''
extern "C" PyObject *%(FUNC_NAME)s(PyObject *parent)
{
    PyObject *m = CreateModule("%(MNAME_FULL)s");
    if (m == NULL) {
        return NULL;
    }

    if (parent) {
        Py_INCREF(m);
        PyModule_AddObject(parent, (char *) "%(MNAME)s", m);
    }
'''

#---------------------------------------------------------------------------#

offset_base_ptr_sig = 'static void OffsetBasePtr(PyTypeObject *base_type, void **base_ptr)'

pyobj_decl = '''typedef struct {
    PyObject_HEAD
    %%(WRAPT)s *obj;
    FpOffsetBase fp_offset_base;
    wxBinderFlags flags:8;
} %%(PYOBJ_NAME)s;

%s;
extern PyTypeObject %%(PYTYPE_NAME)s;
''' % offset_base_ptr_sig

#---------------------------------------------------------------------------#

ctor_sig = '''static int %(CTOR_NAME)s
    (%(PYOBJ_NAME)s *self, PyObject *args, PyObject *kwargs)'''

ctor_uninstanizable_error = '''PyErr_SetString(PyExc_TypeError, "class `%(CLS_NAME)s` cannot be constructed.");
PyErr_Print();
return -1;'''

ctor_chk_abstract = '''if (Py_TYPE(self) == &%%(PYTYPE_NAME)s) {
>>>
%s
<<<
}
''' % ctor_uninstanizable_error

ctor_actions_more = '''self->flags = %s;
self->fp_offset_base = OffsetBasePtr;'''

#---------------------------------------------------------------------------#

dtor = '''static void %(DTOR_NAME)s(%(PYOBJ_NAME)s *self)
{
    %(WRAPT)s *tmp = self->obj;
    self->obj = NULL;
    if (!(self->flags & wxBF_OBJECT_BORROWED)) {
        delete tmp;
    }

    Py_TYPE(self)->tp_free((PyObject *) self);
}'''

#---------------------------------------------------------------------------#

TestSubclassAndOffset = '''%(WRAPT)s *obj = self->obj;
TestSubclassAndOffset(self, %(MY_PYTYPE)s, obj);
'''

offset_base_ptr = offset_base_ptr_sig + '''
{
    if (base_type == &%s) {
        return;
    }

    unsigned long p = (unsigned long) *base_ptr;
    if (0) {}'''

offset_base_ptr_item = '''else if (base_type == &%(BASE_PYTYPE)s) {
    p += (unsigned long)(((%(BASE)s *)((%(WRAPT)s *) 100))) - 100;
    *base_ptr = (void *) p;
}'''

register_bases_sig = 'extern "C" static void %s__Bases()'
register_enums_sig = 'extern "C" static void %s__Enums()'

base_tuple_item = '''Py_INCREF((PyObject *) &%(BASE_TYPE)s);
PyTuple_SET_ITEM(%(DERIVED_TYPE)s.tp_bases, %(INDEX)d, (PyObject *) &%(BASE_TYPE)s);'''

register_class = '''extern "C" void %(REGISTER)s(PyObject *m)
{
    %(PYSIDE)s__Bases();

    if (PyType_Ready(&%(PYTYPE)s) == 0) {
        %(ACTION)s
        %(PYSIDE)s__Enums();
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
}
'''

register_class_enum_values = '''
RegisterEnumValues(__values, %s.tp_dict);'''

#---------------------------------------------------------------------------#

PyArg_ParseTupleAndKeywords = (
    'PyArg_ParseTupleAndKeywords(%(TUPLE)s, %(KW_TUPLE)s, %(FORMAT)s, (char **) %(KW_ARRAY)s, %(ARGS)s)'
)

PyArg_ParseTuple = (
    'PyArg_ParseTuple(%(TUPLE)s, %(FORMAT)s, %(ARGS)s)'
)

Py_BuildValue = (
    'Py_BuildValue((char *) %(FORMAT)s, %(BUILDER)s(%(CVAL)s))'
)


PyCapsule_New = 'PyObject *py_%s = PyCapsule_New((void *) %s, "%s", NULL);'

wrap_nontrivial_borrowed_ref = '''
%(PYOBJ_STRUCT)s *py_%(VAR_NAME)s = NULL;
if (typeid(%(REF)s).name() == typeid(%(WRAPT)s).name()) {
    py_%(VAR_NAME)s = (%(PYOBJ_STRUCT)s *) ((%(WRAPT)s *) (%(ADDR)s))->self;
    Py_INCREF(py_%(VAR_NAME)s);
}
else {
    py_%(VAR_NAME)s = PyObject_New(%(PYOBJ_STRUCT)s, &%(PYTYPE)s);
    py_%(VAR_NAME)s->obj = (%(WRAPT)s *) (%(ADDR)s);
    py_%(VAR_NAME)s->fp_offset_base = OffsetBasePtr;
    py_%(VAR_NAME)s->flags = wxBF_OBJECT_BORROWED;
}
'''

ensure_not_null = '''if (!retval) {
    Py_RETURN_NONE;
}
'''

exporter = '''PyObject *Export__%(CLS_EMBBEDED)s(const %(CLASS)s &other, wxBinderFlags flags)
{
    %(PYOBJ_STRUCT)s *pyobj = PyObject_New(%(PYOBJ_STRUCT)s, &%(PYTYPE)s);
    pyobj->obj = (%(WRAPT)s *) new %(CLASS)s(other);
    pyobj->fp_offset_base = OffsetBasePtr;
    pyobj->flags = flags;

    return (PyObject *) pyobj;
}
'''

return_by_value = '''
PyObject *Export__%(CLS_EMBBEDED)s(const %(CLASS)s &other, wxBinderFlags flags);
PyObject *py_retval = Export__%(CLS_EMBBEDED)s(retval, wxBF_NONE);'''

to_built_in_type = "%(CTYPE)s %(VAL)s = static_cast<%(CTYPE)s>(%(EXTRACTOR)s(%(PYOBJ)s));"

cast_external = (
    '*((%(CLASS)s **) (((unsigned long) %(PYOBJ_PTR)s) + sizeof(PyObject)))'
)

#---------------------------------------------------------------------------#

method_sig = "static PyObject *%(NAME)s(%(PYOBJ_NAME)s *self, PyObject *args, PyObject *kwargs)"
method_sig_no_arg = "static PyObject *%(NAME)s(%(PYOBJ_NAME)s *self)"

ff_sig = "static PyObject *__%(NAME)s(PyObject *WXBINDER_UNUSED(m), PyObject *args, PyObject *kwargs)"
ff_sig_no_arg = "static PyObject *__%(NAME)s()"

method_table_begin = "static PyMethodDef _methods[] = {"
method_table_end = '''    {  NULL, NULL, 0, NULL }
};
'''

#---------------------------------------------------------------------------#

overloading_arg_parsing_label = "__%(FUNC_NAME)s_OVERLOAD_%(INDEX)d"

overloading_arg_parsing_err_handler = '''PyObject *exc_type, *traceback;
PyErr_Fetch(&exc_type, &exceptions[%(INDEX)d], &traceback);
Py_XDECREF(exc_type);
Py_XDECREF(traceback);

%(ERR_RETURN)s'''

overloading_arg_parsing_err_return = '''
PyList_SET_ITEM(error_list, %(INDEX)d, PyObject_Str(exceptions[%(INDEX)d]));
Py_DECREF(exceptions[%(INDEX)d]);'''

overloading_arg_parsing_set_exception = '''

PyErr_SetObject(PyExc_TypeError, error_list);
Py_DECREF(error_list);

'''

#---------------------------------------------------------------------------#

throw_cxxexception = 'throw %(EXCEPTION)s("%(RET)s %(SIG)s");'
invoke_def_impl = 'return %(WRAPT)s::%(MNAME)s(%(ARGS)s);'

handle_return_void = '''if (callback_retval != Py_None) {
    Py_XDECREF(callback_retval);
    PyErr_Print();
    throw CallPyMethodError("%s");
}'''


handle_return_non_void = '''if (callback_retval == NULL) {
>>>
%s
<<<
}

PyObjectPtr retval_tuple(Py_BuildValue("(N)", callback_retval));
'''


def virtual_method_wrapper_header(pure_virtual):
    boilerplate = '''PyObjectPtr py_method(PyObject_GetAttrString(self, (char *) "%%(MNAME)s"));
PyErr_Clear();

if (!py_method || Py_TYPE(py_method) == &PyCFunction_Type ||
    GetMethodArgsCount(py_method) != (%%(ARGS_COUNT)d + 1)) {
        %s
}

PyObject *callback_retval = PyObject_CallMethod(self, (char *) "%%(MNAME)s", %%(CM_ARGS)s);'''

    if pure_virtual:
        return boilerplate % throw_cxxexception.replace(
            "%(EXCEPTION)s", "PureVirtualFunctionNotImplemented", 1
        )
    else:
        return boilerplate % invoke_def_impl