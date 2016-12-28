#include "def.hpp"

int foo(map<const char *, int> &dict) {
    dict["price"] = 456;
    dict["index"] = 999;
}
