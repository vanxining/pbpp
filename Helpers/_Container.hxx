#pragma once
#include "_Python.hxx"

namespace Python {
    
    template <class T>
    struct const_ref {
        typedef const T &type;
    };

    template <class T>
    struct const_ref<const T> {
        typedef const T &type;
    };

    template <class T>
    struct const_ref<const T &> {
        typedef const T &type;
    };

    template <class T>
    struct const_ref<T *> {
        typedef T *type;
    };

    template <class T>
    struct const_ref<const T *> {
        typedef const T *type;
    };

    enum ReferenceType {
        VALUE, /*! 值复制 */
        CONST_VALUE, /*! 常量值复制 */
        REF, /*! 引用 */
        CONST_REF, /*! 对常量引用 */
        PTR, /*! 指针 */
        CONST_PTR /*! 常量指针 */
    };

    /// 容器转换器基类
    template <class Cont>
    class Container {
    public:

        /// 构造函数
        Container(PyObject *obj, ReferenceType type)
            : m_obj(obj), m_type(type), m_defv(nullptr) {
        }

        /// 设置默认值
        void SetDefault(const Cont &defv) {
            m_defv = const_cast<Cont *>(&defv);
        }

        /// 设置默认值
        void SetDefault(const Cont *defv) {
            m_defv = const_cast<Cont *>(defv);
        }

        /// 两步构造法：避免使用异常
        bool ConvertFromPython() {
            if (m_obj && m_obj != Py_None) {
                return DoConvertFromPython();
            }

            return true;
        }

        /// 析构函数
        virtual ~Container() {}

    protected:

        /// Python -> C++
        virtual bool DoConvertFromPython() = 0;

        /// C++ -> Python
        virtual void DoConvertBackToPython() = 0;

        /// 尝试回写到 Python
        void TryConvertBackToPython() {
            if (m_obj) {
                if (m_type == REF || (m_type == PTR && m_obj != Py_None)) {
                    DoConvertBackToPython();
                }
            }
        }

    public:

        operator Cont &() {
            return (m_obj) ? m_cont : *m_defv;
        }

        operator Cont *() {
            if (m_obj) {
                return (m_obj == Py_None) ? nullptr : &m_cont;
            }
            else {
                return m_defv;
            }
        }

    protected:

        PyObject *m_obj;
        ReferenceType m_type;

        Cont *m_defv;
        Cont m_cont;
    };
}
