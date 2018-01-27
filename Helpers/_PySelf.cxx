#include "_PySelf.hxx"
#include "_Common.hxx"

//////////////////////////////////////////////////////////////////////////////

_PySelf::_PySelf()
    : m_self(nullptr), m_cloned(false) {}

_PySelf::~_PySelf() {
    if (!m_self) {
        return;
    }

    if (m_cloned) {
        PBPP_NEW_THREAD_BLOCKER
        Py_DECREF(m_self);
    }
}

void _PySelf::SetSelf(PyObject *self, bool clone) {
    PBPP_NEW_THREAD_BLOCKER

    if (m_self && m_cloned) {
        Py_DECREF(m_self);
    }

    m_self = self;
    m_cloned = false;

    if (m_self && clone) {
        Py_INCREF(m_self);
        m_cloned = true;
    }
}

PyObject *_PySelf::GetSelf() const {
    if (m_self) {
        PBPP_NEW_THREAD_BLOCKER
        Py_INCREF(m_self);
    }

    return m_self;
}
