#include "_Python.hxx"
#include "_Common.hxx"

%(HEADERS)s

/* ------------------------------------------------------------------------ */

%(FPTRS)s%(FREE_FUNCTIONS)s

#if PY_VERSION_HEX >= 0x03000000
static struct PyModuleDef %(MNAME)s_moduledef = {
     PyModuleDef_HEAD_INIT,
    "%(MNAME_FULL)s",
     nullptr,
    -1,
    _methods,
};
#endif


/* ------------------------------------------------------------------------ */
