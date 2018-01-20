///////////////////////////////////////////
// A, B, C: Test whether the generated code compiles
class A {
    A();
    A(const A &);

public:

    static A &get() {
        return staticA;
    }

    int count = 999;

    static A staticA;
};

struct B {
    A a;
};

struct C : B {
    int i;
};

///////////////////////////////////////////
// D, E, F: Test getting and setting fields of "class value" type
struct D {
    D() : a(A::staticA) {}

    virtual int foo() = 0;

    A &a;
};

struct Field {
    int num = 0;
};

struct E : D {
    int bar();

    Field field;
};

struct F : E {
    virtual int foo();
};

F tmp_f();

///////////////////////////////////////////
// G, H: Test non-copyable fields
class G {
    G(const G &);

public:
    G() {}

    Field field;
};

struct H {
    ~H();

    G g;
};

struct wstring {
    wstring(const wchar_t *str = L"Hello, world!") : str(str) {}

    unsigned int length() const;
    const wchar_t *c_str() const;

    const wchar_t *str;
};

///////////////////////////////////////////
// I: Test:
//    * C++'s implicit copy constructor
//    * copying types with type converter
struct I {
    int num = 0;
    wstring str;
};
