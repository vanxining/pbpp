#ifndef __CASTXML__

#include <map>
#include <string>

using namespace std;

#else

template <class K, class V>
class map;

class wstring;

#endif

int foo(map<wstring, int> &dict);
