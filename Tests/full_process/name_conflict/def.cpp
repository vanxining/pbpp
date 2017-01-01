#include "def.hpp"

int foo(int m, int args, int kwargs, double py_args, double py_kwargs) {
    return static_cast<int>(m + args + kwargs + py_args + py_kwargs);
}
