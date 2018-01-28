"""
The class PyTypeObject generates a PyTypeObject structure contents.
"""


class PyTypeObject(object):
    TEMPLATE = (
        'PyTypeObject %(typestruct)s = {\n'
        '     PyVarObject_HEAD_INIT(nullptr, 0)\n'
        '    "%(tp_name)s", /* tp_name */\n'
        '    (Py_ssize_t) %(tp_basicsize)s, /* tp_basicsize */\n'
        '    (Py_ssize_t) 0, /* tp_itemsize */\n'
        '    (destructor) %(tp_dealloc)s, /* tp_dealloc */\n'
        '    (printfunc) 0, /* tp_print */\n'
        '    (getattrfunc) %(tp_getattr)s, /* tp_getattr */\n'
        '    (setattrfunc) %(tp_setattr)s, /* tp_setattr */\n'
        '     nullptr, /* tp_compare, tp_as_async */\n'
        '    (reprfunc) %(tp_repr)s, /* tp_repr */\n'
        '    (PyNumberMethods *) %(tp_as_number)s, /* tp_as_number */\n'
        '    (PySequenceMethods *) %(tp_as_sequence)s, /* tp_as_sequence */\n'
        '    (PyMappingMethods *) %(tp_as_mapping)s, /* tp_as_mapping */\n'
        '    (hashfunc) %(tp_hash)s, /* tp_hash */\n'
        '    (ternaryfunc) %(tp_call)s, /* tp_call */\n'
        '    (reprfunc) %(tp_str)s, /* tp_str */\n'
        '    (getattrofunc) %(tp_getattro)s, /* tp_getattro */\n'
        '    (setattrofunc) %(tp_setattro)s, /* tp_setattro */\n'
        '    (PyBufferProcs *) %(tp_as_buffer)s, /* tp_as_buffer */\n'
        '     %(tp_flags)s, /* tp_flags */\n'
        '     %(tp_doc)s, /* Documentation string */\n'
        '    (traverseproc) %(tp_traverse)s, /* tp_traverse */\n'
        '    (inquiry) %(tp_clear)s, /* tp_clear */\n'
        '    (richcmpfunc) %(tp_richcompare)s, /* tp_richcompare */\n'
        '     %(tp_weaklistoffset)s, /* tp_weaklistoffset */\n'
        '    (getiterfunc) %(tp_iter)s, /* tp_iter */\n'
        '    (iternextfunc) %(tp_iternext)s, /* tp_iternext */\n'
        '    (PyMethodDef *) %(tp_methods)s, /* tp_methods */\n'
        '    (PyMemberDef *) nullptr, /* tp_members */\n'
        '     %(tp_getset)s, /* tp_getset */\n'
        '     nullptr, /* tp_base */\n'
        '     nullptr, /* tp_dict */\n'
        '    (descrgetfunc) %(tp_descr_get)s, /* tp_descr_get */\n'
        '    (descrsetfunc) %(tp_descr_set)s, /* tp_descr_set */\n'
        '     %(tp_dictoffset)s, /* tp_dictoffset */\n'
        '    (initproc) %(tp_init)s, /* tp_init */\n'
        '    (allocfunc) %(tp_alloc)s, /* tp_alloc */\n'
        '    (newfunc) %(tp_new)s, /* tp_new */\n'
        '    (freefunc) %(tp_free)s, /* tp_free */\n'
        '    (inquiry) %(tp_is_gc)s, /* tp_is_gc */\n'
        '     nullptr, /* tp_bases */\n'
        '     nullptr, /* tp_mro */\n'
        '     nullptr, /* tp_cache */\n'
        '     nullptr, /* tp_subclasses */\n'
        '     nullptr, /* tp_weaklist */\n'
        '    (destructor) nullptr /* tp_del */\n'
        '};\n'
    )

    def __init__(self):
        self.slots = {}

    def generate(self, code_sink):
        slots = dict(self.slots)

        slots.setdefault('tp_dealloc', 'nullptr')
        slots.setdefault('tp_getattr', 'nullptr')
        slots.setdefault('tp_setattr', 'nullptr')
        slots.setdefault('tp_compare', 'nullptr')  # Python 2
        slots.setdefault('tp_as_async', 'nullptr')  # Python 3
        slots.setdefault('tp_repr', 'nullptr')
        slots.setdefault('tp_as_number', 'nullptr')
        slots.setdefault('tp_as_sequence', 'nullptr')
        slots.setdefault('tp_as_mapping', 'nullptr')
        slots.setdefault('tp_hash', 'nullptr')
        slots.setdefault('tp_call', 'nullptr')
        slots.setdefault('tp_str', 'nullptr')
        slots.setdefault('tp_getattro', 'nullptr')
        slots.setdefault('tp_setattro', 'nullptr')
        slots.setdefault('tp_as_buffer', 'nullptr')
        slots.setdefault('tp_flags', 'Py_TPFLAGS_DEFAULT')
        slots.setdefault('tp_doc', 'nullptr')
        slots.setdefault('tp_traverse', 'nullptr')
        slots.setdefault('tp_clear', 'nullptr')
        slots.setdefault('tp_richcompare', 'nullptr')
        slots.setdefault('tp_weaklistoffset', '0')
        slots.setdefault('tp_iter', 'nullptr')
        slots.setdefault('tp_iternext', 'nullptr')
        slots.setdefault('tp_methods', 'nullptr')
        slots.setdefault('tp_getset', 'nullptr')
        slots.setdefault('tp_descr_get', 'nullptr')
        slots.setdefault('tp_descr_set', 'nullptr')
        slots.setdefault('tp_dictoffset', '0')
        slots.setdefault('tp_init', 'nullptr')
        slots.setdefault('tp_alloc', 'PyType_GenericAlloc')
        slots.setdefault('tp_new', 'PyType_GenericNew')
        slots.setdefault('tp_free', 'PyObject_Del')
        slots.setdefault('tp_is_gc', 'nullptr')

        code_sink.write_code(self.TEMPLATE % slots)


class PyNumberMethods(object):
    TEMPLATE = (
        'static PyNumberMethods %(variable)s = {\n'
        '#if PY_VERSION_HEX < 0x03000000\n'
        '    (binaryfunc) %(nb_add)s,\n'
        '    (binaryfunc) %(nb_subtract)s,\n'
        '    (binaryfunc) %(nb_multiply)s,\n'
        '    (binaryfunc) %(nb_divide)s,\n'
        '    (binaryfunc) %(nb_remainder)s,\n'
        '    (binaryfunc) %(nb_divmod)s,\n'
        '    (ternaryfunc) %(nb_power)s,\n'
        '    (unaryfunc) %(nb_negative)s,\n'
        '    (unaryfunc) %(nb_positive)s,\n'
        '    (unaryfunc) %(nb_absolute)s,\n'
        '    (inquiry) %(nb_nonzero)s,\n'
        '    (unaryfunc) %(nb_invert)s,\n'
        '    (binaryfunc) %(nb_lshift)s,\n'
        '    (binaryfunc) %(nb_rshift)s,\n'
        '    (binaryfunc) %(nb_and)s,\n'
        '    (binaryfunc) %(nb_xor)s,\n'
        '    (binaryfunc) %(nb_or)s,\n'
        '    (coercion) %(nb_coerce)s,\n'
        '    (unaryfunc) %(nb_int)s,\n'
        '    (unaryfunc) %(nb_long)s,\n'
        '    (unaryfunc) %(nb_float)s,\n'
        '    (unaryfunc) %(nb_oct)s,\n'
        '    (unaryfunc) %(nb_hex)s,\n'
        '    /* Added in release 2.0 */\n'
        '    (binaryfunc) %(nb_inplace_add)s,\n'
        '    (binaryfunc) %(nb_inplace_subtract)s,\n'
        '    (binaryfunc) %(nb_inplace_multiply)s,\n'
        '    (binaryfunc) %(nb_inplace_divide)s,\n'
        '    (binaryfunc) %(nb_inplace_remainder)s,\n'
        '    (ternaryfunc) %(nb_inplace_power)s,\n'
        '    (binaryfunc) %(nb_inplace_lshift)s,\n'
        '    (binaryfunc) %(nb_inplace_rshift)s,\n'
        '    (binaryfunc) %(nb_inplace_and)s,\n'
        '    (binaryfunc) %(nb_inplace_xor)s,\n'
        '    (binaryfunc) %(nb_inplace_or)s,\n'
        '\n'
        '    /* Added in release 2.2 */\n'
        '    /* The following require the Py_TPFLAGS_HAVE_CLASS flag */\n'
        '    (binaryfunc) %(nb_floor_divide)s,\n'
        '    (binaryfunc) %(nb_true_divide)s,\n'
        '    (binaryfunc) %(nb_inplace_floor_divide)s,\n'
        '    (binaryfunc) %(nb_inplace_true_divide)s,\n'
        '\n'
        '#if PY_VERSION_HEX >= 0x020500F0\n'
        '    /* Added in release 2.5 */\n'
        '    (unaryfunc) %(nb_index)s,\n'
        '\n'
        '#endif\n'

        '#else /* Python 3 changed this structure a lot */\n'

        '(binaryfunc) %(nb_add)s,\n'
        '(binaryfunc) %(nb_subtract)s,\n'
        '(binaryfunc) %(nb_multiply)s,\n'
        '(binaryfunc) %(nb_remainder)s,\n'
        '(binaryfunc) %(nb_divmod)s,\n'
        '(ternaryfunc) %(nb_power)s,\n'
        '(unaryfunc) %(nb_negative)s,\n'
        '(unaryfunc) %(nb_positive)s,\n'
        '(unaryfunc) %(nb_absolute)s,\n'
        '(inquiry) %(nb_bool)s,\n'
        '(unaryfunc) %(nb_invert)s,\n'
        '(binaryfunc) %(nb_lshift)s,\n'
        '(binaryfunc) %(nb_rshift)s,\n'
        '(binaryfunc) %(nb_and)s,\n'
        '(binaryfunc) %(nb_xor)s,\n'
        '(binaryfunc) %(nb_or)s,\n'
        '(unaryfunc) %(nb_int)s,\n'
        'nullptr,\n'
        '(unaryfunc) %(nb_float)s,\n'
        '\n'
        '(binaryfunc) %(nb_inplace_add)s,\n'
        '(binaryfunc) %(nb_inplace_subtract)s,\n'
        '(binaryfunc) %(nb_inplace_multiply)s,\n'
        '(binaryfunc) %(nb_inplace_remainder)s,\n'
        '(ternaryfunc) %(nb_inplace_power)s,\n'
        '(binaryfunc) %(nb_inplace_lshift)s,\n'
        '(binaryfunc) %(nb_inplace_rshift)s,\n'
        '(binaryfunc) %(nb_inplace_and)s,\n'
        '(binaryfunc) %(nb_inplace_xor)s,\n'
        '(binaryfunc) %(nb_inplace_or)s,\n'
        '\n'
        '(binaryfunc) %(nb_floor_divide)s,\n'
        '(binaryfunc) %(nb_divide)s,\n'
        '(binaryfunc) %(nb_inplace_floor_divide)s,\n'
        '(binaryfunc) %(nb_inplace_divide)s,\n'
        '\n'
        '(unaryfunc) %(nb_index)s,\n'
        '#endif\n'
        
        '};\n'
    )

    def __init__(self):
        self.slots = {}

    def generate(self, code_sink):
        """
        Generates the structure.  All slots are optional except 'variable'.
        """

        slots = dict(self.slots)

        slots.setdefault('nb_add', 'nullptr')
        slots.setdefault('nb_bool', 'nullptr')
        slots.setdefault('nb_subtract', 'nullptr')
        slots.setdefault('nb_multiply', 'nullptr')
        slots.setdefault('nb_divide', 'nullptr')
        slots.setdefault('nb_remainder', 'nullptr')
        slots.setdefault('nb_divmod', 'nullptr')
        slots.setdefault('nb_power', 'nullptr')
        slots.setdefault('nb_negative', 'nullptr')
        slots.setdefault('nb_positive', 'nullptr')
        slots.setdefault('nb_absolute', 'nullptr')
        slots.setdefault('nb_nonzero', 'nullptr')
        slots.setdefault('nb_invert', 'nullptr')
        slots.setdefault('nb_lshift', 'nullptr')
        slots.setdefault('nb_rshift', 'nullptr')
        slots.setdefault('nb_and', 'nullptr')
        slots.setdefault('nb_xor', 'nullptr')
        slots.setdefault('nb_or', 'nullptr')
        slots.setdefault('nb_coerce', 'nullptr')
        slots.setdefault('nb_int', 'nullptr')
        slots.setdefault('nb_long', 'nullptr')
        slots.setdefault('nb_float', 'nullptr')
        slots.setdefault('nb_oct', 'nullptr')
        slots.setdefault('nb_hex', 'nullptr')
        slots.setdefault('nb_inplace_add', 'nullptr')
        slots.setdefault('nb_inplace_subtract', 'nullptr')
        slots.setdefault('nb_inplace_multiply', 'nullptr')
        slots.setdefault('nb_inplace_divide', 'nullptr')
        slots.setdefault('nb_inplace_remainder', 'nullptr')
        slots.setdefault('nb_inplace_power', 'nullptr')
        slots.setdefault('nb_inplace_lshift', 'nullptr')
        slots.setdefault('nb_inplace_rshift', 'nullptr')
        slots.setdefault('nb_inplace_and', 'nullptr')
        slots.setdefault('nb_inplace_xor', 'nullptr')
        slots.setdefault('nb_inplace_or', 'nullptr')
        slots.setdefault('nb_floor_divide', 'nullptr')
        slots.setdefault('nb_true_divide', 'nullptr')
        slots.setdefault('nb_inplace_floor_divide', 'nullptr')
        slots.setdefault('nb_inplace_true_divide', 'nullptr')
        slots.setdefault('nb_index', 'nullptr')

        code_sink.write_code(self.TEMPLATE % slots)

class PySequenceMethods(object):
    TEMPLATE = '''
static PySequenceMethods %(variable)s = {
    (lenfunc) %(sq_length)s,
    (binaryfunc) %(sq_concat)s,
    (ssizeargfunc) %(sq_repeat)s,
    (ssizeargfunc) %(sq_item)s,
#if PY_MAJOR_VERSION < 3
    (ssizessizeargfunc) %(sq_slice)s,
#else
    nullptr,
#endif
    (ssizeobjargproc) %(sq_ass_item)s,
#if PY_MAJOR_VERSION < 3
    (ssizessizeobjargproc) %(sq_ass_slice)s,
#else
    nullptr,
#endif
    (objobjproc) %(sq_contains)s,
    /* Added in release 2.0 */
    (binaryfunc) %(sq_inplace_concat)s,
    (ssizeargfunc) %(sq_inplace_repeat)s,
};

'''

    FUNCTION_TEMPLATES = {
        # __len__
        "sq_length" : '''
static Py_ssize_t
%(wrapper_name)s (%(py_struct)s *py_self)
{
    PyObject *py_result;
    Py_ssize_t result;

    py_result = %(method_name)s(py_self);
    if (py_result == nullptr) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error in attempting to determine __len__.");
        Py_XDECREF(py_result);
        return -1;
    }
    result = PyLong_AsSsize_t(py_result);
    Py_DECREF(py_result);
    return result;
}

''',

        # __len__
        # This hacky version is necessary 'cause if we're calling a function rather than a method
        # or an overloaded wrapper the args parameter gets tacked into the call sequence.
        "sq_length_ARGS" : '''
static Py_ssize_t
%(wrapper_name)s (%(py_struct)s *py_self)
{
    PyObject *py_result;
    PyObject *args;
    Py_ssize_t result;

    args = PyTuple_New (0);
    py_result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    if (py_result == nullptr) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error in attempting to determine __len__.");
        Py_XDECREF(py_result);
        return -1;
    }
    result = PyLong_AsSsize_t(py_result);
    Py_DECREF(py_result);
    return result;
}

''',

        # __add__ (concatenation)
        "sq_concat" : '''
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, %(py_struct)s *py_rhs)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(O)", py_rhs);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    return result;
}

''',

        # __mul__ (repeat)
        "sq_repeat" : '''
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(i)", py_i);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    return result;
}

''',

        # __getitem__
        "sq_item" : '''
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(i)", py_i);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    if (PyErr_ExceptionMatches(PyExc_IndexError) ||
        PyErr_ExceptionMatches(PyExc_StopIteration)) {
        Py_XDECREF(result);
        return nullptr;
    } else {
        return result;
    }
}


''',

        # __getslice__
        "sq_slice" : '''
#if PY_MAJOR_VERSION < 3
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i1, Py_ssize_t py_i2)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(ii)", py_i1, py_i2);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    if (PyErr_ExceptionMatches(PyExc_IndexError) ||
        PyErr_ExceptionMatches(PyExc_StopIteration)) {
        Py_XDECREF(result);
        return nullptr;
    } else {
        return result;
    }
}
#endif
''',

        # __setitem__
        "sq_ass_item" : '''
static int
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i, PyObject *py_val)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(iO)", py_i, py_val);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    if (result == nullptr) {
        PyErr_SetString(PyExc_IndexError, "Unknown error trying to set value in container.");
        return -1;
#if PY_MAJOR_VERSION >= 3
    } else if (PyLong_Check(result) == 0) {
#else
    } else if (PyInt_Check(result) == 0) {
#endif
        PyErr_SetString(PyExc_IndexError, "Error trying to set value in container -- wrapped method should return integer status.");
        return -1;
    } else {
#if PY_MAJOR_VERSION >= 3
        int iresult = int(PyLong_AS_LONG(result));
#else
        int iresult = int(PyInt_AS_LONG(result));
#endif
        Py_DECREF(result);
        return iresult;
    }
}

''',

        # __setslice__
        "sq_ass_slice" : '''
#if PY_MAJOR_VERSION < 3
static int
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i1, Py_ssize_t py_i2, %(py_struct)s *py_vals)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(iiO)", py_i1, py_i2, py_vals);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    if (result == nullptr) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error trying to set slice in container.");
        return -1;
    } else if (PyInt_Check(result) == 0) {
        PyErr_SetString(PyExc_RuntimeError, "Error trying to set slice in container -- wrapped method should return integer status.");
        return -1;
    } else {
        int iresult = int(PyInt_AS_LONG(result));
        Py_DECREF(result);
        return iresult;
    }
}
#endif
''',

        # __contains__
        "sq_contains" : '''
static int
%(wrapper_name)s (%(py_struct)s *py_self, PyObject *py_val)
{
    PyObject* result;
    PyObject *args;

    args = Py_BuildValue("(O)", py_val);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
#if PY_MAJOR_VERSION >= 3
    if (result == nullptr || PyLong_Check(result) == 0) {
#else
    if (result == nullptr || PyInt_Check(result) == 0) {
#endif
        PyErr_SetString(PyExc_RuntimeError, "Unknown error in attempting to test __contains__.");
        Py_XDECREF(result);
        return -1;
    } else {
#if PY_MAJOR_VERSION >= 3
        int iresult = int(PyLong_AS_LONG(result));
#else
        int iresult = int(PyInt_AS_LONG(result));
#endif
        Py_DECREF(result);
        return iresult;
    }
}

''',

        # __iadd__ (in-place concatenation)
        "sq_inplace_concat" : '''
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, %(py_struct)s *py_rhs)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(O)", py_rhs);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    return result;
}

''',

        # __imul__ (in-place repeat)
        "sq_inplace_repeat" : '''
static PyObject*
%(wrapper_name)s (%(py_struct)s *py_self, Py_ssize_t py_i)
{
    PyObject *result;
    PyObject *args;

    args = Py_BuildValue("(i)", py_i);
    result = %(method_name)s(py_self, args, nullptr);
    Py_DECREF(args);
    return result;
}

''',

    }

    def __init__(self):
        self.slots = {}

    def generate(self, code_sink):
        """
        Generates the structure.  All slots are optional except 'variable'.
        """

        slots = dict(self.slots)

        slots.setdefault('sq_length', 'nullptr')
        slots.setdefault('sq_concat', 'nullptr')
        slots.setdefault('sq_repeat', 'nullptr')
        slots.setdefault('sq_item', 'nullptr')
        slots.setdefault('sq_slice', 'nullptr')
        slots.setdefault('sq_ass_item', 'nullptr')
        slots.setdefault('sq_ass_slice', 'nullptr')
        slots.setdefault('sq_contains', 'nullptr')
        slots.setdefault('sq_inplace_concat', 'nullptr')
        slots.setdefault('sq_inplace_repeat', 'nullptr')

        code_sink.write_code(self.TEMPLATE % slots)
