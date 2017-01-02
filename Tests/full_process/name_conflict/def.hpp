struct A {
    virtual ~A() {}

    virtual int foo(int py_method, int py_vm_retval);

    int call_foo(int py_method, int py_vm_retval) {
        return foo(py_method, py_vm_retval);
    }
};

int foo(int m, int args, int kwargs, double py_args, double py_kwargs);
