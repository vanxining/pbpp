/***************************************************************
 * Name:      _Common.hxx
 * Purpose:   一些公用辅助设施
 * Author:    Wang Xiaoning (vanxining@139.com)
 * Created:   2014
 **************************************************************/
#pragma once
#include "_Python.hxx"

#ifndef PyVarObject_HEAD_INIT
#   define PyVarObject_HEAD_INIT(type, size) \
           PyObject_HEAD_INIT(type) size,
#endif

#if PY_VERSION_HEX >= 0x03000000
    typedef void *cmpfunc;
#   define PyString_FromString(a) PyBytes_FromString(a)
#   define Py_TPFLAGS_CHECKTYPES 0 // This flag doesn't exist in Python 3
#endif

#if __GNUC__ > 2
#   define PBPP_UNUSED(param) param __attribute__((__unused__))
#elif __GNUC__ > 2 || (__GNUC__ == 2 && __GNUC_MINOR__ > 4)
#   define PBPP_UNUSED(param) __attribute__((__unused__)) param
#else
#   define PBPP_UNUSED(param)
#endif

#if PY_VERSION_HEX >= 0x03000000
#   define EXPORT_MOD(mod_name) \
        PyMODINIT_FUNC PyInit_ ## mod_name() { \
            return mod_name(nullptr); \
        } \
    
#   define CreateModule(mod_name) PyModule_Create(&mod_name ## _moduledef)
#else
#   define EXPORT_MOD(mod_name) \
        PyMODINIT_FUNC init ## mod_name() { \
            mod_name(nullptr); \
        } \
    
#   define CreateModule(mod_name) \
        Py_InitModule3((char *) mod_name, __methods, nullptr)
#endif

#define ___OVERLOAD___()
#define ___SCOPE___()

//////////////////////////////////////////////////////////////////////////

/// 修正基类指针偏移
/// 
/// 因为 Python 对我们的 C++ 对象（甚至语言）一无所知，当我们在 Python 代码中使用
/// 一个非主基类的方法/成员变量时，Python 使用的是派生类的 PyObject 对象，其中
/// 的 cxx_obj 属性是派生类指针。
/// 这种情况下，我们需要手动将这个派生类指针转为非主基类指针。
typedef void *(*FpOffsetBase)(void *cxx_obj, PyTypeObject *base_type);

namespace pbpp {

/// Python 对象对应的 C++ 对象的生命周期管理策略
namespace LifeTime {
enum {
    /// C++ 对象的生命周期跟随 Python 对象（默认）
    PYTHON = 1 << 0,

    /// C++ 对象的生命周期独立于对应的 Python 对象，且持有 Python 对象的
    /// 一个引用
    /// 
    /// 一般应用场景是 C++ 端需要调用 Python 派生类中的虚函数，此时一个显然的
    /// 要求是我们此时必须保证 Python 对象仍然存在。
    /// 注意：这种情况下 C++ 对象可能先于 Python 对象被析构，此时 Python 对象
    /// 已然无效，若从 Python 端继续使用该对象，那么程序的行为是未定义的。
    CXX = 1 << 1,

    /// 借用的 C++ 对象，其生命周期与对应的 Python 对象无关
    /// 
    /// 实际上 C++ 对象与 Python 对象两者的析构时机之间无任何关系。
    BORROWED = 1 << 2,
};
}

}

typedef unsigned short pbpp_flag_t;

//////////////////////////////////////////////////////////////////////////

#include <initializer_list>

namespace pbpp {

/// 获取函数对象的参数个数
int GetMethodArgsCount(PyObject *py_method);

/// 将一组数字打包成 Python 元组
PyObject *PackAsTuple(const std::initializer_list<int> &numbers);

/// 自动销毁一个异常对象数组
/// 
/// 为支持函数重载，我们在解析函数参数时临时保存了尝试某个重载失败时
/// PyArg_ParseTupleAndKeywords() 给出的参数类型不匹配异常对象。
/// 这个类的目的就是从包裹函数返回时自动销毁这些缓存对象。
class ExceptionArrayDestructor {
public:

    /// 构造函数
    ExceptionArrayDestructor(PyObject **exceptions);

    /// 析构函数
    ~ExceptionArrayDestructor();

private:

    PyObject **exceptions;
};

/// 取出当前 Python 解释器异常对象并将其缓存到 @a exception
void CachePythonException(PyObject **exception);

/// 将缓存的异常对象数组转发到 Python
/// 
/// 代表没有合适的重载调用。
void RestorePythonExceptions(PyObject **exceptions, int n);

//////////////////////////////////////////////////////////////////////////

namespace Types {

/// 是否为整数
/// 
/// 包括 PyInt (Python 2.x) 以及 PyLong。
bool IsInteger(PyObject *obj);

/// 是否为数字
/// 
/// 包括 PyInt (Python 2.x), PyLong, PyFloat。
bool IsNumber(PyObject *obj);

/// 转换为整形
/// 
/// 不会检查 @a obj 是否确实为一个数字。
/// @return 若返回 -1，需要调用者检查是否出现了错误还是正确结果确实是 -1。
int ToInt(PyObject *obj);

/// 转换为无符号整形
unsigned int ToUnsignedInt(PyObject *obj);

/// 转换为长整形
long ToLong(PyObject *obj);

/// 转换为无符号长整形
unsigned long ToUnsignedLong(PyObject *obj);

/// 转换为长长整形
long long ToLongLong(PyObject *obj);

/// 转换为无符号长长整形
unsigned long long ToUnsignedLongLong(PyObject *obj);

/// 转换为双精度浮点数
double ToDouble(PyObject *obj);

/// 转换为短整型
short ToShort(PyObject *obj);

/// 转换为无符号短整型
unsigned short ToUnsignedShort(PyObject *obj);

/// 转换为 wchar_t
/// 
/// 没有 unsigned wchar_t。
wchar_t ToWChar(PyObject *obj);

/// 转换为 char
/// 
char ToChar(PyObject *obj);

/// 转换为 unsigned char
unsigned char ToUnsignedChar(PyObject *obj);

} // namespace Types

//////////////////////////////////////////////////////////////////////////

/// 来自 C++ 的异常
class CxxException {
public:

    /// 构造函数
    CxxException(PyObject *exception, const char *desc);

public:

    /// 异常对象
    PyObject *exception;
    const char *desc; // 补充描述文本
};

/// 纯虚函数未实现
class PureVirtualFunctionNotImplemented : public CxxException {
public:

    /// 构造函数
    PureVirtualFunctionNotImplemented(const char *desc);
};

/// 从 C++ 调用 Python 函数出现错误
/// 
/// 可能的原因有返回值或参数类型、个数不匹配。
class CallPyMethodError : public CxxException {
public:

    /// 构造函数
    CallPyMethodError(const char *desc);
};

/// 空引用
class NullReferenceError : public CxxException {
public:

    NullReferenceError(const char *desc);
};

/// 参数类型错误
class ArgumentTypeError : public CxxException {
public:

    /// 构造函数
    ArgumentTypeError(const char *desc);
};

} // namespace pbpp

//////////////////////////////////////////////////////////////////////////

/// PyObject 智能指针
/// 
/// @todo 移入 pbpp 命名空间
class PyObjectPtr {
public:

    /// 显式构造函数
    explicit PyObjectPtr(PyObject *ptr, bool borrowed = false)
        : m_ptr(ptr), m_borrowed(borrowed) {}

    /// 析构函数
    ~PyObjectPtr();

    /// 获取 PyObject 指针
    operator PyObject *() { return m_ptr; }
    PyObject *get() const { return m_ptr; }

    /// 测试是否为空
    operator bool() { return m_ptr != nullptr;  }

    /// 释放 PyObject 指针
    void release();

private:

    // 不能复制
    PyObjectPtr(const PyObjectPtr &) = delete;
    PyObjectPtr &operator=(const PyObjectPtr &) = delete;

private:

    PyObject *m_ptr;
    bool m_borrowed;
};

//////////////////////////////////////////////////////////////////////////

namespace pbpp {

/// 用于关于强类型枚举的若干情景
struct ScopedEnumDummy {};

} // namespace pbpp

/// 枚举 key-value 对
struct EnumValue {
    const char *name; /*! 名称 */
    int value; /*! 枚举值 */
};

/// 注册一个枚举键值对数组
void RegisterEnumValues(EnumValue *val, PyObject *tp_dict);

//////////////////////////////////////////////////////////////////////////

#ifdef PBPP_SUPPORT_THREAD

/* Function to check whether the current thread has acquired the GIL.
 * Return 1 if the current thread is holding the GIL and 0 otherwise.
 *
 * This is a kind-of untested backport of
 * https://docs.python.org/3/c-api/init.html?highlight=pygilstate_check#c.PyGILState_Check
 * It can be useful in debugging deadlocks/crashes in python-c api
 * usage by checking whether the GIL is acquired or not where expected.
 * 
 * From: https://github.com/pankajp/pygilstate_check
 */
#if PY_VERSION_HEX < 0x03000000
int PyGILState_Check();
#endif

// Calls from Python to C++ code are wrapped in calls to these
// functions:

inline PyThreadState *PyBeginAllowThreads() {
    return PyEval_SaveThread(); // Py_BEGIN_ALLOW_THREADS
}

inline void PyEndAllowThreads(PyThreadState *saved) {
    PyEval_RestoreThread(saved); // Py_END_ALLOW_THREADS
}

// Calls from C++ back to Python code, or even any PyObject
// manipulations, PyDECREF's and etc. are wrapped in calls to 
// these functions:

PyGILState_STATE PyBeginBlockThreads();
void PyEndBlockThreads(PyGILState_STATE blocked);

/// 一个 RAII 类
class PyThreadBlocker {
public:

    /// 构造函数
    PyThreadBlocker();
    PyThreadBlocker(const PyThreadBlocker &) = delete;
    PyThreadBlocker &operator=(const PyThreadBlocker &) = delete;

    /// 析构函数
    ~PyThreadBlocker();

    /// 提前允许其他线程运行
    void Disable();

private:

    PyGILState_STATE m_state;
    bool m_disabled; // 自身是否已被禁用？(其他线程能否运行？)
};

#define PBPP_BEGIN_ALLOW_THREADS PyThreadState *_saved = PyBeginAllowThreads();
#define PBPP_END_ALLOW_THREADS PyEndAllowThreads(_saved);

#define PBPP_NEW_THREAD_BLOCKER PyThreadBlocker _blocker;
#define PBPP_DISABLE_THREAD_BLOCKER _blocker.Disable();

#else

#define PBPP_BEGIN_ALLOW_THREADS
#define PBPP_END_ALLOW_THREADS

#define PBPP_NEW_THREAD_BLOCKER
#define PBPP_DISABLE_THREAD_BLOCKER

#endif
