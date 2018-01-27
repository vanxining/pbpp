#pragma once
#include "_Container.hxx"

namespace Python {

    /// 实现 Python 的 map 类型与某一 C++ 等价类型之间的转换
    template <class Cont,
              typename KeyExtractor, typename KeyBuilder,
              typename ValExtractor, typename ValBuilder>
    class Dict : public Container<Cont> {
    public:

        typedef Container<Cont> Super;

        /// 构造函数
        Dict(PyObject *obj, ReferenceType type,
             KeyExtractor key_extractor, KeyBuilder key_builder,
             ValExtractor val_extractor, ValBuilder val_builder)
                : Super(obj, type),
                  m_key_extrator(key_extractor),
                  m_key_builder(key_builder),
                  m_val_extrator(val_extractor),
                  m_val_builder(val_builder) {

        }

        /// 析构函数
        ~Dict() {
            Super::TryConvertBackToPython();
        }

    private:

        virtual bool DoConvertFromPython() {
            typename Cont::key_type key;
            typename Cont::mapped_type value;

            PyObject *py_key, *py_value;
            Py_ssize_t pos = 0;

            while (PyDict_Next(Super::m_obj, &pos, &py_key, &py_value)) {
                if (!m_key_extrator(py_key, key)) {
                    return false;
                }

                if (!m_val_extrator(py_value, value)) {
                    return false;
                }

                Super::m_cont[key] = value;
            }

            return true;
        }

        virtual void DoConvertBackToPython() {
            PyDict_Clear(Super::m_obj);

            for (auto &kv : Super::m_cont) {
                PyObject *py_key = nullptr, *py_value = nullptr;

                if (m_key_builder(kv.first, py_key) &&
                    m_val_builder(kv.second, py_value)) {
                        PyDict_SetItem(Super::m_obj, py_key, py_value);
                        Py_DECREF(py_key);
                        Py_DECREF(py_value);
                } else {
                    break;
                }
            }
        }

    private:

        KeyExtractor m_key_extrator;
        KeyBuilder m_key_builder;
        ValExtractor m_val_extrator;
        ValBuilder m_val_builder;
    };
}
