/***************************************************************
 * Name:      _PySelf.hxx
 * Purpose:   保存自身的 PyObject 指针（模拟 self 指针）
 * Author:    Wang Xiaoning (vanxining@139.com)
 * Created:   2014-11-04
 **************************************************************/
#pragma once
#include "_Python.hxx"

/// 保存自身的 PyObject 指针
class _PySelf {
public:
    _PySelf();
    ~_PySelf();

    void SetSelf(PyObject *self, bool clone = false);
    /// return: new reference
    PyObject *GetSelf() const;

    bool IsCloned() const {
        return m_cloned;
    }

protected:

    PyObject *m_self;
    bool m_cloned;
};
