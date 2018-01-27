/***************************************************************
* Name:      _Python.hxx
* Purpose:   <Python.h> °ü¹üÆ÷
* Author:    Wang Xiaoning (vanxining@139.com)
* Created:   2014-9-28
**************************************************************/
#pragma once

#define PY_SSIZE_T_CLEAN

#if !defined PYTHON_DEBUG_BUILD && defined _DEBUG
// Include these low level headers before undefing _DEBUG. Otherwise when doing
// a debug build against a release build of python the compiler will end up
// including these low level headers without DEBUG enabled, causing it to try
// and link release versions of this low level C api.
#   include <basetsd.h>
#   include <assert.h>
#   include <ctype.h>
#   include <errno.h>
#   include <io.h>
#   include <math.h>
#   include <sal.h>
#   include <stdarg.h>
#   include <stddef.h>
#   include <stdio.h>
#   include <stdlib.h>
#   include <string.h>
#   include <sys/stat.h>
#   include <time.h>
#   include <wchar.h>
#	undef _DEBUG
#	include <Python.h>
#	define _DEBUG
#else
#	include <Python.h>
#endif
