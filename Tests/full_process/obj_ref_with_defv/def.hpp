struct dummy {
    dummy(int i) : i(i) {}

    int i;
};

int foo(const dummy &dp = dummy(123));