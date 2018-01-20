#include "def.hpp"

A A::staticA;

A::A() {}
A::A(const A &) {}

int E::bar() {
    return 0;
}

int F::foo() {
    return 5678;
}

G::G(const G &) {}

#include <cstdio>

H::~H() {
    printf("H::~H()\n");
}

F tmp_f() {
    return F();
}

#include <cwchar>

unsigned int wstring::length() const {
    return wcslen(str);
}

const wchar_t *wstring::c_str() const {
    return str;
}
