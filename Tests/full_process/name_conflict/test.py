import unittest


class Test(unittest.TestCase):
    def runTest(self):
        from .. import full_process
        m = full_process.run2(__file__)

        self.assertEqual(m.foo(1, 2, 3, 4.5, 10.5), 21)

        # noinspection PyMethodMayBeStatic
        class A_derived(m.A):
            def foo(self, py_method, py_vm_retval):
                return py_method * py_vm_retval

        self.assertEqual(m.A().call_foo(1, 2), 5)
        self.assertEqual(A_derived().call_foo(1, 2), 2)
