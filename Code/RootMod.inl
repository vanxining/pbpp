
#if PY_VERSION_HEX >= 0x03000000
#   define PBPP_EXPORT_ROOT_MOD(mod_name) \
        PyMODINIT_FUNC PyInit_ ## mod_name() { \
            return mod_name(nullptr); \
        }
#else
#   define PBPP_EXPORT_ROOT_MOD(mod_name) \
        PyMODINIT_FUNC init ## mod_name() { \
            mod_name(nullptr); \
        }
#endif

PBPP_EXPORT_ROOT_MOD(%s)
