#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "_Common.h"
%(HEADERS)s

/* ----------------------------------------------------------------------- */

%(FREE_FUNCTIONS)s

#if PY_VERSION_HEX >= 0x03000000
static struct PyModuleDef %(MNAME)s_moduledef = {
    PyModuleDef_HEAD_INIT,
    "%(MNAME_FULL)s",
    NULL,
    -1,
    _methods,
};
#endif


/* ------------------------------------------------------------------------ */
