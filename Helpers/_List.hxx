#pragma once
#include "_Container.hxx"

namespace Python {
    
    /// 实现 Python 的 list 类型与某一 C++ 等价类型之间的转换
    template <class Cont, typename Extractor, typename Builder>
    class List : public Container<Cont> {
    public:

        typedef Container<Cont> Super;

        /// 构造函数
        List(PyObject *obj, 
             ReferenceType type, 
             Extractor extrator, 
             Builder builder)
                : Super(obj, type),
                  m_item_extrator(extrator),
                  m_item_builder(builder) {

        }

        /// 析构函数
        ~List() {
            Super::TryConvertBackToPython();
        }

    private:

        virtual bool DoConvertFromPython() {
            typename Cont::value_type item;

            Py_ssize_t len = PyList_Size(Super::m_obj);
            for (Py_ssize_t i = 0; i < len; i++) {
                PyObject *py_item = PyList_GetItem(Super::m_obj, i);
                if (!m_item_extrator(py_item, item)) {
                    return false;
                }

                Super::m_cont.push_back(item);
            }

            return true;
        }

        virtual void DoConvertBackToPython() {
            PyList_SetSlice(Super::m_obj,
                            0, PyList_Size(Super::m_obj),
                            nullptr);

            for (auto &item : Super::m_cont) {
                PyObject *py_item = nullptr;

                if (m_item_builder(item, py_item)) {
                    PyList_Append(Super::m_obj, py_item);
                } else {
                    break;
                }
            }
        }

    private:

        Extractor m_item_extrator;
        Builder m_item_builder;
    };
}
