#include "def.hpp"

int A::foo(int py_method, int py_vm_retval) {
    return py_method + py_vm_retval * 2;
}

int foo(int m, int args, int kwargs, double py_args, double py_kwargs) {
    return static_cast<int>(m + args + kwargs + py_args + py_kwargs);
}
