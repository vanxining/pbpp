#include "def.hpp"

int foo(map<wstring, int> &dict) {
    dict[L"price"] = 456;
    dict[L"index"] = 999;
}
