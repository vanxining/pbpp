#pragma once
#include "_Container.hxx"

namespace Python {
    
    /// ʵ�� Python �� list ������ĳһ C++ �ȼ�����֮���ת��
    template <class Cont, typename Extractor, typename Builder>
    class List : public Container<Cont> {
    public:

        /// ���캯��
        List(PyObject *obj, 
             ReferenceType type, 
             Extractor extrator, 
             Builder builder)
                : Container(obj, type),
                  m_item_extrator(extrator),
                  m_item_builder(builder) {

        }

        /// ��������
        ~List() {
            TryConvertBackToPython();
        }

    private:

        virtual bool DoConvertFromPython() {
            typename Cont::value_type item;

            Py_ssize_t len = PyList_Size(m_obj);
            for (Py_ssize_t i = 0; i < len; i++) {
                PyObject *py_item = PyList_GetItem(m_obj, i);
                if (!m_item_extrator(py_item, item)) {
                    return false;
                }

                m_cont.push_back(item);
            }

            return true;
        }

        virtual void DoConvertBackToPython() {
            PyList_SetSlice(m_obj, 0, PyList_Size(m_obj), nullptr);

            for (auto &item : m_cont) {
                PyObject *py_item = nullptr;
                if (m_item_builder(item, py_item)) {
                    PyList_Append(m_obj, py_item);
                }
                else {
                    break;
                }
            }
        }

    private:

        Extractor m_item_extrator;
        Builder m_item_builder;
    };
}