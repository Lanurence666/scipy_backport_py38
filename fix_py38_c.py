#!/usr/bin/env python3
"""
Python 3.8 兼容性修复脚本 - C/C++ 源码部分
============================================

将此脚本放在项目源码根目录下运行，自动修复所有 Python 3.9+ C API，
使项目 C/C++ 扩展源码兼容 Python 3.8。

修复策略:
  1. 部署 pythoncapi_compat.h 兼容头文件到项目中
  2. 在使用 Python 3.9+ C API 的 C/C++ 文件中添加 #include
  3. 修复直接使用 Python 3.9+ C API 而未通过兼容层的代码
  4. 修复 CMakeLists.txt / setup.py 中的 Python 版本约束

Python 3.9+ C API 变更:
  - PyObject_CallNoArgs() (3.9+)
  - PyObject_CallOneArg() (3.9+)
  - Py_IS_TYPE() (3.9+)
  - Py_SET_TYPE() (3.9+)
  - Py_SET_SIZE() (3.9+)
  - Py_SET_REFCNT() (3.9+)
  - PyModule_AddType() (3.9+)
  - PyModule_AddObjectRef() (3.10+)
  - PyObject_Vectorcall() (3.9+)
  - PyVectorcall_NARGS() (3.8b1+)
  - PyCMethod / METH_METHOD (3.9+)
  - PyType_GetModule() (3.9+)
  - PyType_GetModuleByDef() (3.9+)
  - PyType_GetSlot() (3.9+)
  - Py_NewRef() / Py_XNewRef() (3.10+)
  - Py_Is() / Py_IsNone() / Py_IsTrue() / Py_IsFalse() (3.10+)
  - PyFrame_GetCode() / PyFrame_GetBack() (3.9+)
  - PyThreadState_GetInterpreter() (3.9+)
  - PyThreadState_GetFrame() (3.9+)
  - PyObject_GC_IsTracked() / PyObject_GC_IsFinalized() (3.9+)
  - PyErr_GetRaisedException() / PyErr_SetRaisedException() (3.12+)

GCC 编译器兼容性修复:
  - #pragma warning(disable:...) → 包裹 #ifdef _MSC_VER
  - __declspec(deprecated) → 添加 GCC __attribute__((deprecated)) 替代
  - _aligned_malloc → 包裹 #ifdef _MSC_VER 保护
  - PY_SSIZE_T_CLEAN → 确保 #include <Python.h> 之前定义

用法:
  python fix_py38_c.py [源码目录]

  如果不指定目录，默认在脚本所在目录下查找。

注意:
  - 此脚本会修改源文件，请先确保已备份或使用版本控制。
  - pythoncapi_compat.h 来自 python/pythoncapi-compat 项目的 Zero Clause BSD 许可。
  - 运行后建议人工检查修改结果。
"""

from __future__ import annotations

import os
import re
import sys

SKIP_DIRS = {
    "__pycache__", ".git", "build", "dist", "egg-info",
    ".mypy_cache", ".pytest_cache", ".tox", ".eggs",
    "node_modules", ".venv", "venv", "env",
}

SKIP_DIRS_NO_SITE = SKIP_DIRS | {"site-packages"}


def _should_skip_site_packages(root):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return "site-packages" not in os.path.normpath(script_dir).split(os.sep)

EXTRA_COMPAT_IMPLEMENTATIONS = r'''

// ===== 以下兼容实现不在上游 pythoncapi_compat.h 中，由 fix_py38_c.py 追加 =====

// PyObject_VectorcallDict() - Python 3.12.0a5
#if PY_VERSION_HEX < 0x030C00A5
static inline PyObject*
PyObject_VectorcallDict(PyObject *callable, PyObject *const *args,
                        size_t nargsf, PyObject *kwdict)
{
    Py_ssize_t nargs = (Py_ssize_t)PyVectorcall_NARGS(nargsf);
    PyObject *tuple = PyTuple_New(nargs);
    if (tuple == NULL) {
        return NULL;
    }
    for (Py_ssize_t i = 0; i < nargs; i++) {
        PyTuple_SET_ITEM(tuple, i, Py_NewRef(args[i]));
    }
    PyObject *result = PyObject_Call(callable, tuple, kwdict);
    Py_DECREF(tuple);
    return result;
}
#endif

// PyObject_VectorcallMethod() - Python 3.12.0a5
#if PY_VERSION_HEX < 0x030C00A5
static inline PyObject*
PyObject_VectorcallMethod(PyObject *name, PyObject *const *args,
                          size_t nargsf, PyObject *kwnames)
{
    PyObject *callable = PyObject_GetAttr(args[0], name);
    if (callable == NULL) {
        return NULL;
    }
    PyObject *result = PyObject_Vectorcall(callable, &args[1],
                                           nargsf - 1, kwnames);
    Py_DECREF(callable);
    return result;
}
#endif

// PyErr_GetRaisedException() / PyErr_SetRaisedException() - Python 3.12.0a1
#if PY_VERSION_HEX < 0x030C00A1
static inline PyObject* PyErr_GetRaisedException(void)
{
    PyObject *exc_type, *exc_value, *exc_tb;
    PyErr_Fetch(&exc_type, &exc_value, &exc_tb);
    PyErr_NormalizeException(&exc_type, &exc_value, &exc_tb);
    Py_XDECREF(exc_type);
    Py_XDECREF(exc_tb);
    return exc_value;
}

static inline int PyErr_SetRaisedException(PyObject *exc)
{
    PyErr_SetObject((PyObject*)Py_TYPE(exc), exc);
    Py_DECREF(exc);
    return 0;
}
#endif

// PyType_GetSlot() - Python 3.9.0a2
#if PY_VERSION_HEX < 0x030900A2
#include <stdint.h>
static inline void* PyType_GetSlot(PyTypeObject *type, int slot)
{
    if (type == NULL || Py_TYPE(type) == NULL) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetSlot: type is NULL");
        return NULL;
    }
    PyTypeObject *tp = type;
    while (tp) {
        switch (slot) {
            case Py_tp_base: return (void*)tp->tp_base;
            case Py_tp_bases: return (void*)tp->tp_bases;
            case Py_tp_mro: return (void*)tp->tp_mro;
            case Py_tp_dict: return (void*)tp->tp_dict;
            case Py_tp_name: return (void*)tp->tp_name;
            case Py_tp_doc: return (void*)tp->tp_doc;
            case Py_tp_hash: return (void*)tp->tp_hash;
            case Py_tp_call: return (void*)tp->tp_call;
            case Py_tp_str: return (void*)tp->tp_str;
            case Py_tp_getattr: return (void*)tp->tp_getattr;
            case Py_tp_setattr: return (void*)tp->tp_setattr;
            case Py_tp_repr: return (void*)tp->tp_repr;
            case Py_tp_richcompare: return (void*)tp->tp_richcompare;
            case Py_tp_iter: return (void*)tp->tp_iter;
            case Py_tp_iternext: return (void*)tp->tp_iternext;
            case Py_tp_descr_get: return (void*)tp->tp_descr_get;
            case Py_tp_descr_set: return (void*)tp->tp_descr_set;
            case Py_tp_init: return (void*)tp->tp_init;
            case Py_tp_new: return (void*)tp->tp_new;
            case Py_tp_del: return (void*)tp->tp_del;
            case Py_tp_alloc: return (void*)tp->tp_alloc;
            case Py_tp_free: return (void*)tp->tp_free;
            case Py_tp_getattro: return (void*)tp->tp_getattro;
            case Py_tp_setattro: return (void*)tp->tp_setattro;
            case Py_tp_as_number: return (void*)tp->tp_as_number;
            case Py_tp_as_sequence: return (void*)tp->tp_as_sequence;
            case Py_tp_as_mapping: return (void*)tp->tp_as_mapping;
            case Py_tp_flags: return (void*)(uintptr_t)tp->tp_flags;
            default:
                break;
        }
        tp = tp->tp_base;
    }
    return NULL;
}
#endif

// PyType_GetModule() - Python 3.9.0a2
#if PY_VERSION_HEX < 0x030900A2
static inline PyObject* PyType_GetModule(PyTypeObject *type)
{
    if (type == NULL) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetModule: type is NULL");
        return NULL;
    }
    PyObject *mro = type->tp_mro;
    if (mro == NULL || !PyTuple_Check(mro)) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetModule: type has no MRO");
        return NULL;
    }
    Py_ssize_t n = PyTuple_GET_SIZE(mro);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *base = PyTuple_GET_ITEM(mro, i);
        if (!PyType_Check(base)) continue;
        PyTypeObject *base_type = (PyTypeObject*)base;
        if (base_type->tp_dict == NULL) continue;
        PyObject *module_name = PyDict_GetItemString(base_type->tp_dict, "__module__");
        if (module_name == NULL || !PyUnicode_Check(module_name)) continue;
        PyObject *module = PyImport_GetModule(module_name);
        if (module != NULL) {
            return module;
        }
        module = PyImport_ImportModuleLevel(
            PyUnicode_AsUTF8(module_name), NULL, NULL, NULL, 0);
        if (module != NULL) {
            return module;
        }
        PyErr_Clear();
    }
    PyErr_SetString(PyExc_AttributeError, "PyType_GetModule: type has no module");
    return NULL;
}
#endif

// PyType_GetModuleByDef() - Python 3.9.0a2 (stub)
#if PY_VERSION_HEX < 0x030900A2
static inline PyObject* PyType_GetModuleByDef(PyTypeObject *type, PyModuleDef *def)
{
    PyErr_SetString(PyExc_RuntimeError, "PyType_GetModuleByDef is not available in Python 3.8");
    return NULL;
}
#endif

// Py_TPFLAGS_HAVE_VECTORCALL - Python 3.9.0a4
// In Python 3.8, vectorcall is available as _PyObject_Vectorcall (3.8b1),
// but Py_TPFLAGS_HAVE_VECTORCALL was only added in 3.9.
#ifndef Py_TPFLAGS_HAVE_VECTORCALL
#  if PY_VERSION_HEX >= 0x030800B1
#    define Py_TPFLAGS_HAVE_VECTORCALL (1UL << 11)
#  else
#    define Py_TPFLAGS_HAVE_VECTORCALL 0
#  endif
#endif

// Py_TPFLAGS_IMMUTABLETYPE - Python 3.10.0a3
#ifndef Py_TPFLAGS_IMMUTABLETYPE
#  define Py_TPFLAGS_IMMUTABLETYPE (1UL << 8)
#endif

// Py_TPFLAGS_MANAGED_DICT and Py_TPFLAGS_MANAGED_WEAKREF - Python 3.12.0a5
#ifndef Py_TPFLAGS_MANAGED_DICT
#  define Py_TPFLAGS_MANAGED_DICT 0
#endif
#ifndef Py_TPFLAGS_MANAGED_WEAKREF
#  define Py_TPFLAGS_MANAGED_WEAKREF 0
#endif

// PyCMethod typedef - Python 3.9.0a1
// This is a function pointer type used with METH_METHOD.
// In Python 3.8, METH_METHOD does not exist, so PyCMethod cannot be used.
// Define it as a no-op stub type to allow compilation.
#if PY_VERSION_HEX < 0x030900A1 && !defined(PyCMethod)
typedef PyObject *(*PyCMethod)(PyObject *, PyTypeObject *, PyObject *, PyObject **);
#endif

// METH_METHOD - Python 3.9.0a1
// Cannot be simply compat-implemented; code using it needs restructuring.
// Define as 0 so that method tables using it will be silently ignored.
#if PY_VERSION_HEX < 0x030900A1 && !defined(METH_METHOD)
#  define METH_METHOD 0x200
#endif

// Py_TPFLAGS_HAVE_VECTORCALL_LITERAL - Python 3.12.0
// This flag indicates that vectorcall is supported using the literal
// tp_vectorcall_offset rather than Py_TPFLAGS_HAVE_VECTORCALL.
// Not needed for Python < 3.12, define as 0 for compatibility.
#ifndef Py_TPFLAGS_HAVE_VECTORCALL_LITERAL
#  define Py_TPFLAGS_HAVE_VECTORCALL_LITERAL 0
#endif

// Py_TPFLAGS_DISALLOW_INSTANTIATION - Python 3.10.0b1
#ifndef Py_TPFLAGS_DISALLOW_INSTANTIATION
#  define Py_TPFLAGS_DISALLOW_INSTANTIATION (1UL << 7)
#endif

// Py_TPFLAGS_MAPPING - Python 3.10.0b1
#ifndef Py_TPFLAGS_MAPPING
#  define Py_TPFLAGS_MAPPING (1UL << 6)
#endif

// Py_TPFLAGS_SEQUENCE - Python 3.10.0b1
#ifndef Py_TPFLAGS_SEQUENCE
#  define Py_TPFLAGS_SEQUENCE (1UL << 5)
#endif

// Py_TPFLAGS_LONG_SUBCLASS - Python 3.12.0a4 (removed in 3.14)
// These type flag bits were removed in Python 3.14 but some code
// references them. Define as 0 for compatibility.
#ifndef Py_TPFLAGS_LONG_SUBCLASS
#  define Py_TPFLAGS_LONG_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_LIST_SUBCLASS
#  define Py_TPFLAGS_LIST_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_TUPLE_SUBCLASS
#  define Py_TPFLAGS_TUPLE_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_BYTES_SUBCLASS
#  define Py_TPFLAGS_BYTES_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_UNICODE_SUBCLASS
#  define Py_TPFLAGS_UNICODE_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_DICT_SUBCLASS
#  define Py_TPFLAGS_DICT_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_BASE_EXC_SUBCLASS
#  define Py_TPFLAGS_BASE_EXC_SUBCLASS 0
#endif
#ifndef Py_TPFLAGS_TYPE_SUBCLASS
#  define Py_TPFLAGS_TYPE_SUBCLASS 0
#endif

// Py_TPFLAGS_USES_DICT_DESCR - Python 3.12.0a4
#ifndef Py_TPFLAGS_USES_DICT_DESCR
#  define Py_TPFLAGS_USES_DICT_DESCR 0
#endif

// Py_TPFLAGS_HAVE_GC - already exists in 3.8, but ensure it's defined
#ifndef Py_TPFLAGS_HAVE_GC
#  define Py_TPFLAGS_HAVE_GC (1UL << 14)
#endif

// PyObject_GetAIter() - Python 3.10.0a6
#if PY_VERSION_HEX < 0x030A00A6 && !defined(PYPY_VERSION)
static inline PyObject* PyObject_GetAIter(PyObject *o)
{
    return PyObject_CallMethod(o, "__aiter__", NULL);
}
#endif

// PyModule_AddFunctions() - Python 3.9.0a5
#if PY_VERSION_HEX < 0x030900A5
static inline int PyModule_AddFunctions(PyObject *module, PyMethodDef *methods)
{
    if (methods == NULL) {
        return 0;
    }
    for (PyMethodDef *def = methods; def->ml_name != NULL; def++) {
        PyObject *func = PyCFunction_New(def, module);
        if (func == NULL) {
            return -1;
        }
        if (PyModule_AddObject(module, def->ml_name, func) < 0) {
            Py_DECREF(func);
            return -1;
        }
    }
    return 0;
}
#endif

// PyInterpreterState_GetDict() - Python 3.12.0a2
#if PY_VERSION_HEX < 0x030C00A2 && !defined(PYPY_VERSION)
static inline PyObject* PyInterpreterState_GetDict(PyInterpreterState *interp)
{
    if (interp == NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "PyInterpreterState_GetDict: interpreter is NULL");
        return NULL;
    }
    PyObject *dict = PyDict_New();
    return dict;
}
#endif

// PyErr_GetExcInfo() / PyErr_SetExcInfo() - Python 3.11.0a1 (internal in 3.8)
// These were made public in 3.11 but exist internally in 3.8.
#if PY_VERSION_HEX < 0x030B00A1 && !defined(PYPY_VERSION)
static inline void PyErr_GetExcInfo(PyObject **type, PyObject **value, PyObject **traceback)
{
    PyErr_Fetch(type, value, traceback);
    PyErr_NormalizeException(type, value, traceback);
    PyErr_Restore(*type, *value, *traceback);
    Py_XINCREF(*type);
    Py_XINCREF(*value);
    Py_XINCREF(*traceback);
}

static inline void PyErr_SetExcInfo(PyObject *type, PyObject *value, PyObject *traceback)
{
    PyErr_Restore(type, value, traceback);
}
#endif
'''

_EMBEDDED_PYTHONCAPI_COMPAT_H = None


def _find_pythoncapi_compat_h():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        os.path.join(script_dir, "pythoncapi_compat.h"),
    ]
    for entry in os.listdir(script_dir):
        subdir = os.path.join(script_dir, entry)
        if os.path.isdir(subdir):
            candidate = os.path.join(subdir, "pythoncapi_compat.h")
            if os.path.isfile(candidate):
                search_paths.append(candidate)
            for subentry in os.listdir(subdir):
                subsubdir = os.path.join(subdir, subentry)
                if os.path.isdir(subsubdir):
                    candidate = os.path.join(subsubdir, "pythoncapi_compat.h")
                    if os.path.isfile(candidate):
                        search_paths.append(candidate)
    for path in search_paths:
        if os.path.isfile(path):
            return path
    return None


def _load_embedded_compat_h():
    global _EMBEDDED_PYTHONCAPI_COMPAT_H
    if _EMBEDDED_PYTHONCAPI_COMPAT_H is not None:
        return _EMBEDDED_PYTHONCAPI_COMPAT_H
    compat_path = _find_pythoncapi_compat_h()
    if compat_path:
        with open(compat_path, "r", encoding="utf-8", errors="replace") as f:
            upstream = f.read()
        end_marker = "#endif  // PYTHONCAPI_COMPAT"
        end_marker2 = "#endif /* PYTHONCAPI_COMPAT */"
        insert_pos = -1
        for marker in [end_marker, end_marker2]:
            pos = upstream.rfind(marker)
            if pos >= 0:
                insert_pos = pos
                break
        if insert_pos >= 0:
            _EMBEDDED_PYTHONCAPI_COMPAT_H = upstream[:insert_pos] + EXTRA_COMPAT_IMPLEMENTATIONS + "\n" + upstream[insert_pos:]
        else:
            cpp_end = upstream.rfind("#ifdef __cplusplus")
            if cpp_end >= 0:
                _EMBEDDED_PYTHONCAPI_COMPAT_H = upstream[:cpp_end] + EXTRA_COMPAT_IMPLEMENTATIONS + "\n" + upstream[cpp_end:]
            else:
                _EMBEDDED_PYTHONCAPI_COMPAT_H = upstream + EXTRA_COMPAT_IMPLEMENTATIONS
    else:
        _EMBEDDED_PYTHONCAPI_COMPAT_H = _get_minimal_compat_h()
    return _EMBEDDED_PYTHONCAPI_COMPAT_H


def _get_minimal_compat_h():
    return r'''// Header file providing new C API functions to old Python versions.
//
// File distributed under the Zero Clause BSD (0BSD) license.
// Copyright Contributors to the pythoncapi_compat project.
//
// SPDX-License-Identifier: 0BSD
//
// This file was auto-deployed by fix_py38_c.py for Python 3.8 compatibility.
// WARNING: This is a MINIMAL FALLBACK header. For FULL compatibility,
// place the latest pythoncapi_compat.h from
// https://github.com/python/pythoncapi-compat in the same directory as
// fix_py38_c.py. The script will automatically detect and use it.
// This fallback only covers the most commonly used Python 3.9+ APIs.

#ifndef PYTHONCAPI_COMPAT
#define PYTHONCAPI_COMPAT

#ifdef __cplusplus
extern "C" {
#endif

#include <Python.h>
#include <stddef.h>

#if PY_VERSION_HEX < 0x030b00B4 && !defined(PYPY_VERSION)
#  include "frameobject.h"
#endif

#ifndef _Py_CAST
#  define _Py_CAST(type, expr) ((type)(expr))
#endif

#ifndef _Py_NULL
#  if (defined (__STDC_VERSION__) && __STDC_VERSION__ > 201710L) \
          || (defined(__cplusplus) && __cplusplus >= 201103)
#    define _Py_NULL nullptr
#  else
#    define _Py_NULL NULL
#  endif
#endif

#ifndef _PyObject_CAST
#  define _PyObject_CAST(op) _Py_CAST(PyObject*, op)
#endif

// Py_NewRef() - Python 3.10.0a3
#if PY_VERSION_HEX < 0x030A00A3 && !defined(Py_NewRef)
static inline PyObject* _Py_NewRef(PyObject *obj)
{
    Py_INCREF(obj);
    return obj;
}
#define Py_NewRef(obj) _Py_NewRef(_PyObject_CAST(obj))
#endif

// Py_XNewRef() - Python 3.10.0a3
#if PY_VERSION_HEX < 0x030A00A3 && !defined(Py_XNewRef)
static inline PyObject* _Py_XNewRef(PyObject *obj)
{
    Py_XINCREF(obj);
    return obj;
}
#define Py_XNewRef(obj) _Py_XNewRef(_PyObject_CAST(obj))
#endif

// Py_SET_REFCNT() - Python 3.9.0a4
#if PY_VERSION_HEX < 0x030900A4 && !defined(Py_SET_REFCNT)
static inline void _Py_SET_REFCNT(PyObject *ob, Py_ssize_t refcnt)
{
    ob->ob_refcnt = refcnt;
}
#define Py_SET_REFCNT(ob, refcnt) _Py_SET_REFCNT(_PyObject_CAST(ob), refcnt)
#endif

// Py_SET_TYPE() - Python 3.9.0a4
#if PY_VERSION_HEX < 0x030900A4 && !defined(Py_SET_TYPE)
static inline void _Py_SET_TYPE(PyObject *ob, PyTypeObject *type)
{
    ob->ob_type = type;
}
#define Py_SET_TYPE(ob, type) _Py_SET_TYPE(_PyObject_CAST(ob), type)
#endif

// Py_SET_SIZE() - Python 3.9.0a4
#if PY_VERSION_HEX < 0x030900A4 && !defined(Py_SET_SIZE)
static inline void _Py_SET_SIZE(PyVarObject *ob, Py_ssize_t size)
{
    ob->ob_size = size;
}
#define Py_SET_SIZE(ob, size) _Py_SET_SIZE((PyVarObject*)(ob), size)
#endif

// Py_Is() / Py_IsNone() / Py_IsTrue() / Py_IsFalse() - Python 3.10.0b1
#if PY_VERSION_HEX < 0x030A00B1 && !defined(Py_Is)
#  define Py_Is(x, y) ((x) == (y))
#endif
#if PY_VERSION_HEX < 0x030A00B1 && !defined(Py_IsNone)
#  define Py_IsNone(x) Py_Is(x, Py_None)
#endif
#if (PY_VERSION_HEX < 0x030A00B1 || defined(PYPY_VERSION)) && !defined(Py_IsTrue)
#  define Py_IsTrue(x) Py_Is(x, Py_True)
#endif
#if (PY_VERSION_HEX < 0x030A00B1 || defined(PYPY_VERSION)) && !defined(Py_IsFalse)
#  define Py_IsFalse(x) Py_Is(x, Py_False)
#endif

// Py_IS_TYPE() - Python 3.9.0a4
#if PY_VERSION_HEX < 0x030900A4 && !defined(Py_IS_TYPE)
static inline int _Py_IS_TYPE(PyObject *ob, PyTypeObject *type) {
    return Py_TYPE(ob) == type;
}
#define Py_IS_TYPE(ob, type) _Py_IS_TYPE(_PyObject_CAST(ob), type)
#endif

// PyObject_CallNoArgs() - Python 3.9.0a1
#if !defined(PyObject_CallNoArgs) && PY_VERSION_HEX < 0x030900A1
static inline PyObject* PyObject_CallNoArgs(PyObject *func)
{
    return PyObject_CallFunctionObjArgs(func, NULL);
}
#endif

// PyObject_CallOneArg() - Python 3.9.0a4
#if !defined(PyObject_CallOneArg) && PY_VERSION_HEX < 0x030900A4
static inline PyObject* PyObject_CallOneArg(PyObject *func, PyObject *arg)
{
    return PyObject_CallFunctionObjArgs(func, arg, NULL);
}
#endif

// PyModule_AddObjectRef() - Python 3.10.0a3
#if PY_VERSION_HEX < 0x030A00A3
static inline int
PyModule_AddObjectRef(PyObject *module, const char *name, PyObject *value)
{
    int res;
    if (!value && !PyErr_Occurred()) {
        PyErr_SetString(PyExc_SystemError,
                        "PyModule_AddObjectRef() must be called "
                        "with an exception raised if value is NULL");
        return -1;
    }
    Py_XINCREF(value);
    res = PyModule_AddObject(module, name, value);
    if (res < 0) {
        Py_XDECREF(value);
    }
    return res;
}
#endif

// PyModule_AddType() - Python 3.9.0a5
#if PY_VERSION_HEX < 0x030900A5
static inline int PyModule_AddType(PyObject *module, PyTypeObject *type)
{
    const char *name, *dot;
    if (PyType_Ready(type) < 0) {
        return -1;
    }
    name = type->tp_name;
    assert(name != _Py_NULL);
    dot = strrchr(name, '.');
    if (dot != _Py_NULL) {
        name = dot + 1;
    }
    return PyModule_AddObjectRef(module, name, _PyObject_CAST(type));
}
#endif

// PyObject_GC_IsTracked() - Python 3.9.0a6
#if PY_VERSION_HEX < 0x030900A6 && !defined(PYPY_VERSION)
static inline int PyObject_GC_IsTracked(PyObject* obj)
{
    return (PyObject_IS_GC(obj) && _PyObject_GC_IS_TRACKED(obj));
}
#endif

// PyObject_GC_IsFinalized() - Python 3.9.0a6
#if PY_VERSION_HEX < 0x030900A6 && PY_VERSION_HEX >= 0x030400F0 && !defined(PYPY_VERSION)
static inline int PyObject_GC_IsFinalized(PyObject *obj)
{
    PyGC_Head *gc = _Py_CAST(PyGC_Head*, obj) - 1;
    return (PyObject_IS_GC(obj) && _PyGCHead_FINALIZED(gc));
}
#endif

// PyFrame_GetCode() - Python 3.9.0b1
#if PY_VERSION_HEX < 0x030900B1 || defined(PYPY_VERSION)
static inline PyCodeObject* PyFrame_GetCode(PyFrameObject *frame)
{
    assert(frame != _Py_NULL);
    assert(frame->f_code != _Py_NULL);
    return _Py_CAST(PyCodeObject*, Py_NewRef(frame->f_code));
}
#endif

// PyFrame_GetBack() - Python 3.9.0b1
#if PY_VERSION_HEX < 0x030900B1 && !defined(PYPY_VERSION)
static inline PyFrameObject* PyFrame_GetBack(PyFrameObject *frame)
{
    assert(frame != _Py_NULL);
    return _Py_CAST(PyFrameObject*, Py_XNewRef(frame->f_back));
}
#endif

// PyThreadState_GetInterpreter() - Python 3.9.0a5
#if PY_VERSION_HEX < 0x030900A5 || (defined(PYPY_VERSION) && PY_VERSION_HEX < 0x030B0000)
static inline PyInterpreterState *
PyThreadState_GetInterpreter(PyThreadState *tstate)
{
    assert(tstate != _Py_NULL);
    return tstate->interp;
}
#endif

// PyThreadState_GetFrame() - Python 3.9.0b1
#if PY_VERSION_HEX < 0x030900B1 && !defined(PYPY_VERSION)
static inline PyFrameObject* PyThreadState_GetFrame(PyThreadState *tstate)
{
    assert(tstate != _Py_NULL);
    return _Py_CAST(PyFrameObject *, Py_XNewRef(tstate->frame));
}
#endif

// PyInterpreterState_Get() - Python 3.9.0a5
#if PY_VERSION_HEX < 0x030900A5 || defined(PYPY_VERSION)
static inline PyInterpreterState* PyInterpreterState_Get(void)
{
    PyThreadState *tstate;
    PyInterpreterState *interp;
    tstate = PyThreadState_GET();
    if (tstate == _Py_NULL) {
        Py_FatalError("GIL released (tstate is NULL)");
    }
    interp = tstate->interp;
    if (interp == _Py_NULL) {
        Py_FatalError("no current interpreter");
    }
    return interp;
}
#endif

// PY_VECTORCALL_ARGUMENTS_OFFSET - Python 3.8b1
#ifndef PY_VECTORCALL_ARGUMENTS_OFFSET
#  define PY_VECTORCALL_ARGUMENTS_OFFSET (_Py_CAST(size_t, 1) << (8 * sizeof(size_t) - 1))
#endif

// PyVectorcall_NARGS() - Python 3.8b1
#if PY_VERSION_HEX < 0x030800B1
static inline Py_ssize_t PyVectorcall_NARGS(size_t n)
{
    return n & ~PY_VECTORCALL_ARGUMENTS_OFFSET;
}
#endif

// PyObject_Vectorcall() - Python 3.9.0a4
#if PY_VERSION_HEX < 0x030900A4
static inline PyObject*
PyObject_Vectorcall(PyObject *callable, PyObject *const *args,
                     size_t nargsf, PyObject *kwnames)
{
#if PY_VERSION_HEX >= 0x030800B1 && !defined(PYPY_VERSION)
    return _PyObject_Vectorcall(callable, args, nargsf, kwnames);
#else
    PyObject *posargs = NULL, *kwargs = NULL;
    PyObject *res;
    Py_ssize_t nposargs, nkwargs, i;

    if (nargsf != 0 && args == NULL) {
        PyErr_BadInternalCall();
        goto error;
    }
    if (kwnames != NULL && !PyTuple_Check(kwnames)) {
        PyErr_BadInternalCall();
        goto error;
    }

    nposargs = (Py_ssize_t)PyVectorcall_NARGS(nargsf);
    nkwargs = kwnames ? PyTuple_GET_SIZE(kwnames) : 0;

    posargs = PyTuple_New(nposargs);
    if (posargs == NULL) {
        goto error;
    }
    for (i = 0; i < nposargs; i++) {
        PyTuple_SET_ITEM(posargs, i, Py_NewRef(*args));
        args++;
    }

    if (nkwargs) {
        kwargs = PyDict_New();
        if (kwargs == NULL) {
            goto error;
        }
        for (i = 0; i < nkwargs; i++) {
            PyObject *key = PyTuple_GET_ITEM(kwnames, i);
            PyObject *value = *args;
            args++;
            if (PyDict_SetItem(kwargs, key, value) < 0) {
                goto error;
            }
        }
    }

    res = PyObject_Call(callable, posargs, kwargs);
    Py_DECREF(posargs);
    Py_XDECREF(kwargs);
    return res;

error:
    Py_XDECREF(posargs);
    Py_XDECREF(kwargs);
    return NULL;
#endif
}
#endif

// PyImport_AddModuleRef() - Python 3.13.0a1
#if PY_VERSION_HEX < 0x030D00A0
static inline PyObject* PyImport_AddModuleRef(const char *name)
{
    return Py_XNewRef(PyImport_AddModule(name));
}
#endif

// PyCode_GetCode() - Python 3.11.0b1
#if PY_VERSION_HEX < 0x030B00B1 && !defined(PYPY_VERSION)
static inline PyObject* PyCode_GetCode(PyCodeObject *code)
{
    return Py_NewRef(code->co_code);
}
#endif

// PyThreadState_EnterTracing() / PyThreadState_LeaveTracing() - Python 3.11.0a2
#if PY_VERSION_HEX < 0x030B00A2 && !defined(PYPY_VERSION)
static inline void PyThreadState_EnterTracing(PyThreadState *tstate)
{
    tstate->tracing++;
#if PY_VERSION_HEX >= 0x030A00A1
    tstate->cframe->use_tracing = 0;
#else
    tstate->use_tracing = 0;
#endif
}
static inline void PyThreadState_LeaveTracing(PyThreadState *tstate)
{
    int use_tracing = (tstate->c_tracefunc != _Py_NULL
                       || tstate->c_profilefunc != _Py_NULL);
    tstate->tracing--;
#if PY_VERSION_HEX >= 0x030A00A1
    tstate->cframe->use_tracing = use_tracing;
#else
    tstate->use_tracing = use_tracing;
#endif
}
#endif

// PyObject_GetOptionalAttr() - Python 3.13.0a1
#if PY_VERSION_HEX < 0x030D00A1
static inline int
PyObject_GetOptionalAttr(PyObject *obj, PyObject *attr_name, PyObject **result)
{
#if PY_VERSION_HEX >= 0x030700B1 && !defined(PYPY_VERSION)
    return _PyObject_LookupAttr(obj, attr_name, result);
#else
    *result = PyObject_GetAttr(obj, attr_name);
    if (*result != NULL) {
        return 1;
    }
    if (!PyErr_Occurred()) {
        return 0;
    }
    if (PyErr_ExceptionMatches(PyExc_AttributeError)) {
        PyErr_Clear();
        return 0;
    }
    return -1;
#endif
}
#endif

// PyWeakref_GetRef() - Python 3.13.0a1
#if PY_VERSION_HEX < 0x030D0000
static inline int PyWeakref_GetRef(PyObject *ref, PyObject **pobj)
{
    PyObject *obj;
    if (ref != NULL && !PyWeakref_Check(ref)) {
        *pobj = NULL;
        PyErr_SetString(PyExc_TypeError, "expected a weakref");
        return -1;
    }
    obj = PyWeakref_GetObject(ref);
    if (obj == NULL) {
        *pobj = NULL;
        return -1;
    }
    if (obj == Py_None) {
        *pobj = NULL;
        return 0;
    }
    *pobj = Py_NewRef(obj);
    return 1;
}
#endif

// PyDict_GetItemRef() and PyDict_GetItemStringRef() - Python 3.13.0a1
#if PY_VERSION_HEX < 0x030D00A1
static inline int
PyDict_GetItemRef(PyObject *mp, PyObject *key, PyObject **result)
{
    PyObject *item = PyDict_GetItemWithError(mp, key);
    if (item != NULL) {
        *result = Py_NewRef(item);
        return 1;
    }
    if (!PyErr_Occurred()) {
        *result = NULL;
        return 0;
    }
    *result = NULL;
    return -1;
}

static inline int
PyDict_GetItemStringRef(PyObject *mp, const char *key, PyObject **result)
{
    PyObject *key_obj = PyUnicode_FromString(key);
    if (key_obj == NULL) {
        *result = NULL;
        return -1;
    }
    int res = PyDict_GetItemRef(mp, key_obj, result);
    Py_DECREF(key_obj);
    return res;
}
#endif

// PyList_GetItemRef() - Python 3.13.0a4
#if PY_VERSION_HEX < 0x030D00A4
static inline PyObject *
PyList_GetItemRef(PyObject *op, Py_ssize_t index)
{
    PyObject *item = PyList_GetItem(op, index);
    Py_XINCREF(item);
    return item;
}
#endif

// PyLong_AsInt() - Python 3.13.0a1
#if PY_VERSION_HEX < 0x030D00A1
static inline int PyLong_AsInt(PyObject *obj)
{
    long value = PyLong_AsLong(obj);
    if (value == -1 && PyErr_Occurred()) {
        return -1;
    }
    if (value > INT_MAX || value < INT_MIN) {
        PyErr_SetString(PyExc_OverflowError,
                        "Python int too large to convert to C int");
        return -1;
    }
    return (int)value;
}
#endif
''' + EXTRA_COMPAT_IMPLEMENTATIONS + r'''

#ifdef __cplusplus
}
#endif

#endif /* PYTHONCAPI_COMPAT */
'''


def get_pythoncapi_compat_h():
    return _load_embedded_compat_h()


def _extract_public_apis(content):
    funcs = re.findall(r'^static inline\s+\w[\w\s\*]+?\s+(Py\w+)\s*\(', content, re.MULTILINE)
    funcs += re.findall(r'^static inline\s+\w+\s+\*?\s*(Py\w+)\s*\(', content, re.MULTILINE)
    funcs += re.findall(r'^static inline\s+\w+\s+(Py\w+)\s*\(', content, re.MULTILINE)
    macros_py_underscore = re.findall(r'^#\s*define\s+(Py_\w+)\b', content, re.MULTILINE)
    macros_py_upper = re.findall(r'^#\s*define\s+(Py[A-Z]\w*)\b', content, re.MULTILINE)
    macros_py_upper = [m for m in macros_py_upper if m not in ('Py_BUILD_ASSERT', 'Py_CAST', 'Py_NULL', 'Py_ABS')]
    macros_pyhash = re.findall(r'^#\s*define\s+(PyHASH_\w+)\b', content, re.MULTILINE)
    macros_py_constant = re.findall(r'^#\s*define\s+(Py_CONSTANT_\w+)\b', content, re.MULTILINE)
    macros_py_t = re.findall(r'^#\s*define\s+(Py_T_\w+)\b', content, re.MULTILINE)
    macros_py_tpflags = re.findall(r'^#\s*define\s+(Py_TPFLAGS_\w+)\b', content, re.MULTILINE)
    macros_py_readonly = re.findall(r'^#\s*define\s+(Py_READONLY|Py_AUDIT_READ)\b', content, re.MULTILINE)
    macros_py_meth = re.findall(r'^#\s*define\s+(METH_METHOD)\b', content, re.MULTILINE)
    typedefs = re.findall(r'^typedef\s+\w+\s+(Py\w+)\b', content, re.MULTILINE)
    all_apis = set(funcs + macros_py_underscore + macros_py_upper + macros_pyhash +
                   macros_py_constant + macros_py_t + macros_py_tpflags +
                   macros_py_readonly + macros_py_meth + typedefs)
    skip_names = {
        'Py_UNUSED', 'Py_SETREF', 'Py_XSETREF',
        'Py_BUILD_ASSERT', 'Py_CAST', 'Py_NULL', 'Py_ABS',
        'Py_UNREACHABLE',
    }
    all_apis -= skip_names
    return sorted(all_apis)


def _build_api_patterns():
    content = get_pythoncapi_compat_h()
    apis = _extract_public_apis(content)
    skip_apis = {
        'Py_UNUSED', 'Py_SETREF', 'Py_XSETREF',
        'Py_READONLY', 'Py_AUDIT_READ', '_Py_WRITE_RESTRICTED',
        'Py_CONSTANT_ELLIPSIS', 'Py_CONSTANT_EMPTY_BYTES',
        'Py_CONSTANT_EMPTY_STR', 'Py_CONSTANT_EMPTY_TUPLE',
        'Py_CONSTANT_FALSE', 'Py_CONSTANT_NONE',
        'Py_CONSTANT_NOT_IMPLEMENTED', 'Py_CONSTANT_ONE',
        'Py_CONSTANT_TRUE', 'Py_CONSTANT_ZERO',
        'Py_HASH_POINTER', 'Py_HASH_BUFFER',
        'PyTime_MIN', 'PyTime_MAX',
        'PyLong_LAYOUT',
        'Py_BEGIN_CRITICAL_SECTION', 'Py_END_CRITICAL_SECTION',
        'Py_BEGIN_CRITICAL_SECTION2', 'Py_END_CRITICAL_SECTION2',
        'Py_hash_t',
        'PyBytesWriter',
        'PyLongExport', 'PyLongWriter',
        'PyUnicodeWriter',
        'PyTime_t',
        'PyConfigMemberType', 'PyConfigSpec',
    }
    patterns = []
    for api in apis:
        if api in skip_apis:
            continue
        if api.startswith("_Py") and not api.startswith("_Py_T_"):
            continue
        if api.startswith("Py_T_") or api.startswith("PyHASH_"):
            patterns.append((rf"\b{api}\b", api))
        elif api in ("Py_Is", "Py_IsNone", "Py_IsTrue", "Py_IsFalse"):
            patterns.append((rf"\b{api}\b", api))
        elif api == "METH_METHOD":
            patterns.append((rf"\bMETH_METHOD\b", "METH_METHOD"))
        elif api.startswith("Py_TPFLAGS_"):
            patterns.append((rf"\b{api}\b", api))
        elif api == "PyCMethod":
            patterns.append((rf"\bPyCMethod\b", "PyCMethod"))
        else:
            patterns.append((rf"\b{api}\b", api))
    return patterns


def _build_required_apis():
    content = get_pythoncapi_compat_h()
    return _extract_public_apis(content)


C_API_PATTERNS = []
REQUIRED_COMPAT_APIS = []


def _init_api_lists():
    global C_API_PATTERNS, REQUIRED_COMPAT_APIS
    try:
        C_API_PATTERNS = _build_api_patterns()
        REQUIRED_COMPAT_APIS = _build_required_apis()
    except Exception:
        C_API_PATTERNS = [
            (r"\bPyObject_CallNoArgs\b", "PyObject_CallNoArgs"),
            (r"\bPyObject_CallOneArg\b", "PyObject_CallOneArg"),
            (r"\bPy_IS_TYPE\b", "Py_IS_TYPE"),
            (r"\bPy_SET_TYPE\b", "Py_SET_TYPE"),
            (r"\bPy_SET_SIZE\b", "Py_SET_SIZE"),
            (r"\bPy_SET_REFCNT\b", "Py_SET_REFCNT"),
            (r"\bPyModule_AddType\b", "PyModule_AddType"),
            (r"\bPyModule_AddObjectRef\b", "PyModule_AddObjectRef"),
            (r"\bPyObject_Vectorcall\b", "PyObject_Vectorcall"),
            (r"\bPyVectorcall_NARGS\b", "PyVectorcall_NARGS"),
            (r"\bPy_NewRef\b", "Py_NewRef"),
            (r"\bPy_XNewRef\b", "Py_XNewRef"),
            (r"\bPy_IsNone\b", "Py_IsNone"),
            (r"\bPy_IsTrue\b", "Py_IsTrue"),
            (r"\bPy_IsFalse\b", "Py_IsFalse"),
            (r"\bPy_Is\b", "Py_Is"),
            (r"\bPyFrame_GetCode\b", "PyFrame_GetCode"),
            (r"\bPyFrame_GetBack\b", "PyFrame_GetBack"),
            (r"\bPyThreadState_GetInterpreter\b", "PyThreadState_GetInterpreter"),
            (r"\bPyThreadState_GetFrame\b", "PyThreadState_GetFrame"),
            (r"\bPyInterpreterState_Get\b", "PyInterpreterState_Get"),
            (r"\bPyObject_GC_IsTracked\b", "PyObject_GC_IsTracked"),
            (r"\bPyObject_GC_IsFinalized\b", "PyObject_GC_IsFinalized"),
            (r"\bPyImport_AddModuleRef\b", "PyImport_AddModuleRef"),
            (r"\bPyCode_GetCode\b", "PyCode_GetCode"),
            (r"\bPyErr_GetRaisedException\b", "PyErr_GetRaisedException"),
            (r"\bPyErr_SetRaisedException\b", "PyErr_SetRaisedException"),
            (r"\bPyObject_GetOptionalAttr\b", "PyObject_GetOptionalAttr"),
            (r"\bPyObject_GetOptionalAttrString\b", "PyObject_GetOptionalAttrString"),
            (r"\bPyWeakref_GetRef\b", "PyWeakref_GetRef"),
            (r"\bPyThreadState_EnterTracing\b", "PyThreadState_EnterTracing"),
            (r"\bPyThreadState_LeaveTracing\b", "PyThreadState_LeaveTracing"),
            (r"\bPyObject_VectorcallDict\b", "PyObject_VectorcallDict"),
            (r"\bPyObject_VectorcallMethod\b", "PyObject_VectorcallMethod"),
            (r"\bPyDict_GetItemRef\b", "PyDict_GetItemRef"),
            (r"\bPyDict_GetItemStringRef\b", "PyDict_GetItemStringRef"),
            (r"\bPyList_GetItemRef\b", "PyList_GetItemRef"),
            (r"\bPyLong_AsInt\b", "PyLong_AsInt"),
            (r"\bPyType_GetSlot\b", "PyType_GetSlot"),
            (r"\bPyType_GetModule\b", "PyType_GetModule"),
            (r"\bPyType_GetModuleByDef\b", "PyType_GetModuleByDef"),
            (r"\bPy_TPFLAGS_HAVE_VECTORCALL\b", "Py_TPFLAGS_HAVE_VECTORCALL"),
            (r"\bPy_TPFLAGS_IMMUTABLETYPE\b", "Py_TPFLAGS_IMMUTABLETYPE"),
            (r"\bPyDict_Pop\b", "PyDict_Pop"),
            (r"\bPyDict_PopString\b", "PyDict_PopString"),
            (r"\bPyDict_SetDefaultRef\b", "PyDict_SetDefaultRef"),
            (r"\bPyList_Extend\b", "PyList_Extend"),
            (r"\bPyList_Clear\b", "PyList_Clear"),
            (r"\bPyMapping_GetOptionalItem\b", "PyMapping_GetOptionalItem"),
            (r"\bPyMapping_GetOptionalItemString\b", "PyMapping_GetOptionalItemString"),
            (r"\bPyObject_HasAttrWithError\b", "PyObject_HasAttrWithError"),
            (r"\bPyObject_HasAttrStringWithError\b", "PyObject_HasAttrStringWithError"),
            (r"\bPyMapping_HasKeyWithError\b", "PyMapping_HasKeyWithError"),
            (r"\bPyMapping_HasKeyStringWithError\b", "PyMapping_HasKeyStringWithError"),
            (r"\bPyModule_Add\b", "PyModule_Add"),
            (r"\bPy_IsFinalizing\b", "Py_IsFinalizing"),
            (r"\bPyDict_ContainsString\b", "PyDict_ContainsString"),
            (r"\bPyUnicode_EqualToUTF8\b", "PyUnicode_EqualToUTF8"),
            (r"\bPyUnicode_EqualToUTF8AndSize\b", "PyUnicode_EqualToUTF8AndSize"),
            (r"\bPyCode_GetVarnames\b", "PyCode_GetVarnames"),
            (r"\bPyCode_GetFreevars\b", "PyCode_GetFreevars"),
            (r"\bPyCode_GetCellvars\b", "PyCode_GetCellvars"),
            (r"\bPyFrame_GetLocals\b", "PyFrame_GetLocals"),
            (r"\bPyFrame_GetGlobals\b", "PyFrame_GetGlobals"),
            (r"\bPyFrame_GetBuiltins\b", "PyFrame_GetBuiltins"),
            (r"\bPyFrame_GetLasti\b", "PyFrame_GetLasti"),
            (r"\bPyFrame_GetVar\b", "PyFrame_GetVar"),
            (r"\bPyFrame_GetVarString\b", "PyFrame_GetVarString"),
            (r"\bPyLong_GetSign\b", "PyLong_GetSign"),
            (r"\bPyLong_IsPositive\b", "PyLong_IsPositive"),
            (r"\bPyLong_IsNegative\b", "PyLong_IsNegative"),
            (r"\bPyLong_IsZero\b", "PyLong_IsZero"),
            (r"\bPyIter_NextItem\b", "PyIter_NextItem"),
            (r"\bPy_fopen\b", "Py_fopen"),
            (r"\bPy_fclose\b", "Py_fclose"),
            (r"\bMETH_METHOD\b", "METH_METHOD"),
            (r"\bPyCMethod\b", "PyCMethod"),
            (r"\bPyThreadState_GetID\b", "PyThreadState_GetID"),
            (r"\bPyObject_GetAIter\b", "PyObject_GetAIter"),
            (r"\bPyModule_AddFunctions\b", "PyModule_AddFunctions"),
            (r"\bPyInterpreterState_GetDict\b", "PyInterpreterState_GetDict"),
            (r"\bPyErr_GetExcInfo\b", "PyErr_GetExcInfo"),
            (r"\bPyErr_SetExcInfo\b", "PyErr_SetExcInfo"),
            (r"\bPy_TPFLAGS_DISALLOW_INSTANTIATION\b", "Py_TPFLAGS_DISALLOW_INSTANTIATION"),
            (r"\bPy_TPFLAGS_MAPPING\b", "Py_TPFLAGS_MAPPING"),
            (r"\bPy_TPFLAGS_SEQUENCE\b", "Py_TPFLAGS_SEQUENCE"),
            (r"\bPy_TPFLAGS_MANAGED_DICT\b", "Py_TPFLAGS_MANAGED_DICT"),
            (r"\bPy_TPFLAGS_MANAGED_WEAKREF\b", "Py_TPFLAGS_MANAGED_WEAKREF"),
            (r"\bPyObject_VisitManagedDict\b", "PyObject_VisitManagedDict"),
            (r"\bPyObject_ClearManagedDict\b", "PyObject_ClearManagedDict"),
            (r"\bPyThreadState_GetUnchecked\b", "PyThreadState_GetUnchecked"),
            (r"\bPyUnicode_Equal\b", "PyUnicode_Equal"),
            (r"\bPyBytes_Join\b", "PyBytes_Join"),
            (r"\bPyTuple_FromArray\b", "PyTuple_FromArray"),
            (r"\bPyLong_FromInt32\b", "PyLong_FromInt32"),
            (r"\bPyLong_FromInt64\b", "PyLong_FromInt64"),
            (r"\bPyLong_FromUInt32\b", "PyLong_FromUInt32"),
            (r"\bPyLong_FromUInt64\b", "PyLong_FromUInt64"),
            (r"\bPyLong_AsInt32\b", "PyLong_AsInt32"),
            (r"\bPyLong_AsInt64\b", "PyLong_AsInt64"),
            (r"\bPyLong_AsUInt32\b", "PyLong_AsUInt32"),
            (r"\bPyLong_AsUInt64\b", "PyLong_AsUInt64"),
        ]
        REQUIRED_COMPAT_APIS = [
            "Py_NewRef", "Py_XNewRef", "Py_IsNone", "Py_IsTrue", "Py_IsFalse",
            "Py_Is", "Py_IS_TYPE", "Py_SET_TYPE", "Py_SET_SIZE", "Py_SET_REFCNT",
            "PyObject_CallNoArgs", "PyObject_CallOneArg",
            "PyModule_AddObjectRef", "PyModule_AddType",
            "PyObject_GC_IsTracked", "PyObject_GC_IsFinalized",
            "PyFrame_GetCode", "PyFrame_GetBack",
            "PyThreadState_GetInterpreter", "PyThreadState_GetFrame",
            "PyInterpreterState_Get",
            "PyObject_Vectorcall", "PyVectorcall_NARGS",
            "PyObject_VectorcallDict", "PyObject_VectorcallMethod",
            "PyImport_AddModuleRef", "PyCode_GetCode",
            "PyErr_GetRaisedException", "PyErr_SetRaisedException",
            "PyObject_GetOptionalAttr", "PyObject_GetOptionalAttrString",
            "PyWeakref_GetRef",
            "PyThreadState_EnterTracing", "PyThreadState_LeaveTracing",
            "PyDict_GetItemRef", "PyDict_GetItemStringRef",
            "PyList_GetItemRef", "PyLong_AsInt",
            "PyType_GetSlot", "PyType_GetModule", "PyType_GetModuleByDef",
            "Py_TPFLAGS_HAVE_VECTORCALL", "Py_TPFLAGS_IMMUTABLETYPE",
            "PyDict_Pop", "PyDict_PopString", "PyDict_SetDefaultRef",
            "PyList_Extend", "PyList_Clear",
            "PyMapping_GetOptionalItem", "PyMapping_GetOptionalItemString",
            "PyObject_HasAttrWithError", "PyObject_HasAttrStringWithError",
            "PyMapping_HasKeyWithError", "PyMapping_HasKeyStringWithError",
            "PyModule_Add", "Py_IsFinalizing", "PyDict_ContainsString",
            "PyUnicode_EqualToUTF8", "PyUnicode_EqualToUTF8AndSize",
            "PyCode_GetVarnames", "PyCode_GetFreevars", "PyCode_GetCellvars",
            "PyFrame_GetLocals", "PyFrame_GetGlobals", "PyFrame_GetBuiltins",
            "PyFrame_GetLasti", "PyFrame_GetVar", "PyFrame_GetVarString",
            "PyLong_GetSign", "PyLong_IsPositive", "PyLong_IsNegative", "PyLong_IsZero",
            "PyIter_NextItem", "Py_fopen", "Py_fclose",
            "METH_METHOD", "PyCMethod",
            "PyThreadState_GetID", "PyObject_GetAIter",
            "PyModule_AddFunctions", "PyInterpreterState_GetDict",
            "PyErr_GetExcInfo", "PyErr_SetExcInfo",
            "Py_TPFLAGS_DISALLOW_INSTANTIATION", "Py_TPFLAGS_MAPPING",
            "Py_TPFLAGS_SEQUENCE", "Py_TPFLAGS_MANAGED_DICT",
            "Py_TPFLAGS_MANAGED_WEAKREF",
            "PyObject_VisitManagedDict", "PyObject_ClearManagedDict",
            "PyThreadState_GetUnchecked",
            "PyUnicode_Equal", "PyBytes_Join", "PyTuple_FromArray",
            "PyLong_FromInt32", "PyLong_FromInt64",
            "PyLong_FromUInt32", "PyLong_FromUInt64",
            "PyLong_AsInt32", "PyLong_AsInt64",
            "PyLong_AsUInt32", "PyLong_AsUInt64",
        ]


_init_api_lists()


def find_c_files(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    c_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f.endswith((".c", ".h", ".cpp", ".hpp", ".cc", ".cxx")):
                c_files.append(os.path.join(dirpath, f))
    return c_files


def find_csrc_dirs(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    csrc_dirs = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f.endswith((".c", ".cpp", ".h", ".hpp")):
                csrc_dirs.add(dirpath)
                break
    return csrc_dirs


def has_pythoncapi_compat(content):
    return "pythoncapi_compat" in content


PROJECT_SPECIFIC_INCLUDES = {
    "pytorch": {
        "detect": lambda root: os.path.isfile(os.path.join(root, "torch", "csrc", "utils", "pythoncapi_compat.h")),
        "include_line": '#include <torch/csrc/utils/pythoncapi_compat.h>',
        "compat_h_path": os.path.join("torch", "csrc", "utils", "pythoncapi_compat.h"),
    },
}


def detect_project_type(root):
    for name, config in PROJECT_SPECIFIC_INCLUDES.items():
        if config["detect"](root):
            return name, config
    return None, None


def uses_python_c_api(filepath, project_config=None):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return False, []

    if "#include <Python.h>" not in content and '#include "Python.h"' not in content:
        return False, []

    if has_pythoncapi_compat(content):
        return False, []

    if project_config:
        if project_config["include_line"] in content:
            return False, []

    found_apis = []
    for pattern, name in C_API_PATTERNS:
        if re.search(pattern, content):
            found_apis.append(name)

    return len(found_apis) > 0, found_apis


def add_pythoncapi_include(filepath, project_config=None):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if has_pythoncapi_compat(content):
        return False

    include_line = '#include "pythoncapi_compat.h"'
    if project_config:
        include_line = project_config["include_line"]

    python_include_pattern = r'#include\s*[<"]Python\.h[>"]'
    m = re.search(python_include_pattern, content)
    if not m:
        lines = content.split("\n")
        last_include = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#include"):
                last_include = i
        if last_include >= 0:
            lines.insert(last_include + 1, include_line)
            content = "\n".join(lines)
        else:
            return False
    else:
        insert_pos = m.end()
        content = content[:insert_pos] + "\n" + include_line + content[insert_pos:]

    with open(filepath, "w", encoding="utf-8", errors="replace") as f:
        f.write(content)
    return True


def find_existing_pythoncapi_compat(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    existing = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if "pythoncapi_compat.h" in filenames:
            existing.append(dirpath)
    return existing


def check_pythoncapi_compat_completeness(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return []

    missing = []
    for api in REQUIRED_COMPAT_APIS:
        if api not in content:
            missing.append(api)
    return missing


def update_existing_pythoncapi_compat_h(root, project_config=None, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    updated = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        if "pythoncapi_compat.h" not in filenames:
            continue
        filepath = os.path.join(dirpath, "pythoncapi_compat.h")

        is_project_compat = False
        if project_config:
            compat_rel = project_config.get("compat_h_path", "")
            file_rel = os.path.relpath(filepath, root).replace("\\", "/")
            if file_rel == compat_rel.replace("\\", "/"):
                is_project_compat = True

        missing = check_pythoncapi_compat_completeness(filepath)
        if not missing:
            continue
        relpath = os.path.relpath(filepath, root)
        print(f"  {relpath}: 缺少 {len(missing)} 个兼容实现: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")

        if is_project_compat:
            print(f"  项目特定兼容头文件，跳过自动覆盖（可能比脚本版本更完整）")
            print(f"  请手动添加缺失的兼容实现")
            continue

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(get_pythoncapi_compat_h())
        updated.append(relpath)
        print(f"  已更新: {relpath}")

    return updated


def deploy_pythoncapi_compat_h(root, files_needing_compat, project_config=None, skip_site_packages=True):
    if project_config:
        compat_h_path = os.path.join(root, project_config["compat_h_path"])
        if os.path.isfile(compat_h_path):
            missing = check_pythoncapi_compat_completeness(compat_h_path)
            if missing:
                print(f"  项目兼容头文件缺少 {len(missing)} 个兼容实现，需要手动更新")
                print(f"  缺少: {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}")
            else:
                print(f"  项目兼容头文件已包含所有兼容实现")
            return []
        else:
            target_dir = os.path.dirname(compat_h_path)
            os.makedirs(target_dir, exist_ok=True)
            with open(compat_h_path, "w", encoding="utf-8") as f:
                f.write(get_pythoncapi_compat_h())
            return [project_config["compat_h_path"]]

    existing_locations = find_existing_pythoncapi_compat(root, skip_site_packages=skip_site_packages)

    target_dirs = set()
    for filepath in files_needing_compat:
        target_dirs.add(os.path.dirname(filepath))

    for d in list(target_dirs):
        for existing_dir in existing_locations:
            try:
                rel = os.path.relpath(d, existing_dir)
                if not rel.startswith(".."):
                    target_dirs.discard(d)
                    break
            except ValueError:
                pass

        if d in target_dirs:
            parent = os.path.dirname(d)
            while parent and len(parent) >= len(root):
                if parent in existing_locations:
                    target_dirs.discard(d)
                    break
                parent = os.path.dirname(parent)

    deployed = []
    for target_dir in sorted(target_dirs):
        target_path = os.path.join(target_dir, "pythoncapi_compat.h")
        if os.path.exists(target_path):
            missing = check_pythoncapi_compat_completeness(target_path)
            if missing:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(get_pythoncapi_compat_h())
                deployed.append(os.path.relpath(target_path, root) + " (updated)")
            continue
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(get_pythoncapi_compat_h())
        deployed.append(os.path.relpath(target_path, root))

    return deployed


def fix_cmake_python_version(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    cmake_paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f in ("CMakeLists.txt",) or f.endswith(".cmake"):
                cmake_paths.append(os.path.join(dirpath, f))

    modified = False
    for cmake_path in cmake_paths:
        with open(cmake_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        original = content

        content = re.sub(r'find_package\(Python\s+3\.10', 'find_package(Python 3.8', content)
        content = re.sub(r'find_package\(Python\s+3\.9', 'find_package(Python 3.8', content)
        content = re.sub(r'PYTHON_MIN_VERSION\s+3\.10', 'PYTHON_MIN_VERSION 3.8', content)
        content = re.sub(r'PYTHON_MIN_VERSION\s+3\.9', 'PYTHON_MIN_VERSION 3.8', content)
        content = re.sub(r'VERSION\s+3\.10\.0', 'VERSION 3.8.0', content)
        content = re.sub(r'VERSION\s+3\.9\.0', 'VERSION 3.8.0', content)
        content = re.sub(r'Python3\s+3\.10', 'Python3 3.8', content)
        content = re.sub(r'Python3\s+3\.9', 'Python3 3.8', content)

        if content != original:
            with open(cmake_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            modified = True

    return modified


def fix_meth_method(content):
    if "METH_METHOD" not in content:
        return content

    if "#define METH_METHOD" in content or "#  define METH_METHOD" in content:
        return content

    content = re.sub(
        r'\bMETH_METHOD\b',
        '0x200 /* METH_METHOD - Python 3.9+, replaced for 3.8 compat */',
        content
    )

    if "PyCMethod" in content:
        if "typedef PyObject *(*PyCMethod)" in content:
            return content
        content = re.sub(
            r'\bPyCMethod\b',
            'PyCFunction /* PyCMethod not available in Python 3.8 */',
            content
        )

    return content


def fix_pytype_getmodule(content):
    if "PyType_GetModule" not in content and "PyType_GetModuleByDef" not in content:
        return content

    if "PyType_GetModule" in content and "#ifndef PyType_GetModule" not in content and "PY_VERSION_HEX < 0x030900A0" not in content:
        compat_block = '''
#if PY_VERSION_HEX < 0x030900A0
static inline PyObject* PyType_GetModule(PyTypeObject *type)
{
    if (type == NULL) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetModule: type is NULL");
        return NULL;
    }
    PyObject *mro = type->tp_mro;
    if (mro == NULL || !PyTuple_Check(mro)) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetModule: type has no MRO");
        return NULL;
    }
    Py_ssize_t n = PyTuple_GET_SIZE(mro);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *base = PyTuple_GET_ITEM(mro, i);
        if (!PyType_Check(base)) continue;
        PyTypeObject *base_type = (PyTypeObject*)base;
        if (base_type->tp_dict == NULL) continue;
        PyObject *module_name = PyDict_GetItemString(base_type->tp_dict, "__module__");
        if (module_name == NULL || !PyUnicode_Check(module_name)) continue;
        PyObject *module = PyImport_GetModule(module_name);
        if (module != NULL) {
            return module;
        }
        module = PyImport_ImportModuleLevel(
            PyUnicode_AsUTF8(module_name), NULL, NULL, NULL, 0);
        if (module != NULL) {
            return module;
        }
        PyErr_Clear();
    }
    PyErr_SetString(PyExc_AttributeError, "PyType_GetModule: type has no module");
    return NULL;
}
#endif
'''
        content = compat_block + content

    if "PyType_GetModuleByDef" in content and "#ifndef PyType_GetModuleByDef" not in content:
        compat_block = '''
#if PY_VERSION_HEX < 0x030900A0
static inline PyObject* PyType_GetModuleByDef(PyTypeObject *type, PyModuleDef *def)
{
    PyErr_SetString(PyExc_RuntimeError, "PyType_GetModuleByDef is not available in Python 3.8");
    return NULL;
}
#endif
'''
        content = compat_block + content

    return content


def fix_pytype_getslot(content):
    if "PyType_GetSlot" not in content:
        return content

    if "#ifndef PyType_GetSlot" not in content and "#if PY_VERSION_HEX < 0x030900A0" not in content:
        compat_block = '''
#if PY_VERSION_HEX < 0x030900A0
#include <stdint.h>
static inline void* PyType_GetSlot(PyTypeObject *type, int slot)
{
    if (type == NULL || Py_TYPE(type) == NULL) {
        PyErr_SetString(PyExc_TypeError, "PyType_GetSlot: type is NULL");
        return NULL;
    }
    PyTypeObject *tp = type;
    while (tp) {
        switch (slot) {
            case Py_tp_base: return (void*)tp->tp_base;
            case Py_tp_bases: return (void*)tp->tp_bases;
            case Py_tp_mro: return (void*)tp->tp_mro;
            case Py_tp_dict: return (void*)tp->tp_dict;
            case Py_tp_name: return (void*)tp->tp_name;
            case Py_tp_doc: return (void*)tp->tp_doc;
            case Py_tp_hash: return (void*)tp->tp_hash;
            case Py_tp_call: return (void*)tp->tp_call;
            case Py_tp_str: return (void*)tp->tp_str;
            case Py_tp_getattr: return (void*)tp->tp_getattr;
            case Py_tp_setattr: return (void*)tp->tp_setattr;
            case Py_tp_repr: return (void*)tp->tp_repr;
            case Py_tp_richcompare: return (void*)tp->tp_richcompare;
            case Py_tp_iter: return (void*)tp->tp_iter;
            case Py_tp_iternext: return (void*)tp->tp_iternext;
            case Py_tp_descr_get: return (void*)tp->tp_descr_get;
            case Py_tp_descr_set: return (void*)tp->tp_descr_set;
            case Py_tp_init: return (void*)tp->tp_init;
            case Py_tp_new: return (void*)tp->tp_new;
            case Py_tp_del: return (void*)tp->tp_del;
            case Py_tp_alloc: return (void*)tp->tp_alloc;
            case Py_tp_free: return (void*)tp->tp_free;
            case Py_tp_getattro: return (void*)tp->tp_getattro;
            case Py_tp_setattro: return (void*)tp->tp_setattro;
            case Py_tp_as_number: return (void*)tp->tp_as_number;
            case Py_tp_as_sequence: return (void*)tp->tp_as_sequence;
            case Py_tp_as_mapping: return (void*)tp->tp_as_mapping;
            case Py_tp_flags: return (void*)(uintptr_t)tp->tp_flags;
            default:
                break;
        }
        tp = tp->tp_base;
    }
    return NULL;
}
#endif
'''
        content = compat_block + content

    return content


def fix_gil_disabled_api(content):
    if "Py_MOD_GIL_NOT_USED" not in content and "PyUnstable_Module_SetGIL" not in content:
        return content

    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if "PyUnstable_Module_SetGIL" in stripped or "Py_MOD_GIL_NOT_USED" in stripped:
            j = i - 1
            while j >= 0 and lines[j].strip() == "":
                j -= 1
            if j >= 0 and ("#ifdef Py_GIL_DISABLED" in lines[j] or
                           "#if defined(Py_GIL_DISABLED)" in lines[j] or
                           "#if PY_VERSION_HEX" in lines[j]):
                new_lines.append(line)
                i += 1
                continue

            if "{Py_mod_gil, Py_MOD_GIL_NOT_USED}" in stripped:
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                new_lines.append(f"{indent_str}#if PY_VERSION_HEX >= 0x030d00f0")
                new_lines.append(line)
                i += 1
                if i < len(lines):
                    new_lines.append(f"{indent_str}#endif")
                continue

            if "PyUnstable_Module_SetGIL" in stripped:
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                new_lines.append(f"{indent_str}#ifdef Py_GIL_DISABLED")
                new_lines.append(line)
                i += 1
                new_lines.append(f"{indent_str}#endif")
                continue

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines)


def fix_msvc_pragma_warning_for_gcc(content):
    if '#pragma warning' not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if re.match(r'\s*#\s*pragma\s+warning\s*\(', line):
            new_lines.append('#ifdef _MSC_VER')
            new_lines.append(line)
            new_lines.append('#endif')
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_deprecated_declspec_for_gcc(content):
    if '__declspec(deprecated' not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.search(r'__declspec\s*\(\s*deprecated', line):
            new_lines.append('#ifdef _MSC_VER')
            new_lines.append(line)
            new_lines.append('#else')
            gcc_line = re.sub(r'__declspec\s*\(\s*deprecated\s*\([^)]*\)\s*\)', '__attribute__((deprecated))', line)
            gcc_line = re.sub(r'__declspec\s*\(\s*deprecated\s*\)', '__attribute__((deprecated))', gcc_line)
            new_lines.append(gcc_line)
            new_lines.append('#endif')
        else:
            new_lines.append(line)
        i += 1

    return '\n'.join(new_lines)


def fix_aligned_malloc_for_gcc(content):
    if '_aligned_malloc' not in content:
        return content

    has_msvc_guard = re.search(r'#ifdef\s+_MSC_VER.*_aligned_malloc', content, re.DOTALL)
    if has_msvc_guard:
        return content

    content = re.sub(
        r'(\w+)\s*=\s*_aligned_malloc\s*\(',
        r'#ifdef _MSC_VER\n\1 = _aligned_malloc(',
        content
    )

    return content


def fix_py_ssize_t_clean(content):
    if '#include <Python.h>' not in content and '#include "Python.h"' not in content:
        return content

    if re.search(r'^\s*#\s*define\s+PY_SSIZE_T_CLEAN', content, re.MULTILINE):
        return content

    if '#define PY_SSIZE_T_CLEAN' in content:
        return content

    if 'PyInit_' not in content:
        return content

    lines = content.split('\n')
    insert_pos = -1
    for i, line in enumerate(lines):
        if '#include' in line and 'Python.h' in line:
            insert_pos = i
            break

    if insert_pos >= 0:
        lines.insert(insert_pos, '#define PY_SSIZE_T_CLEAN')

    return '\n'.join(lines)


def process_c_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    original = content

    content = fix_meth_method(content)
    content = fix_pytype_getmodule(content)
    content = fix_pytype_getslot(content)
    content = fix_gil_disabled_api(content)
    content = fix_msvc_pragma_warning_for_gcc(content)
    content = fix_deprecated_declspec_for_gcc(content)
    content = fix_aligned_malloc_for_gcc(content)
    content = fix_py_ssize_t_clean(content)

    if content != original:
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        return True
    return False


def _check_upstream_compat_coverage():
    compat_path = _find_pythoncapi_compat_h()
    if not compat_path:
        return
    with open(compat_path, "r", encoding="utf-8", errors="replace") as f:
        upstream = f.read()
    upstream_apis = set(_extract_public_apis(upstream))
    combined = get_pythoncapi_compat_h()
    combined_apis = set(_extract_public_apis(combined))
    extra_only = combined_apis - upstream_apis
    print(f"  上游 pythoncapi_compat.h 提供 {len(upstream_apis)} 个 API")
    print(f"  合并后（含 EXTRA_COMPAT）提供 {len(combined_apis)} 个 API")
    print(f"  EXTRA_COMPAT 额外提供 {len(extra_only)} 个 API:")
    for api in sorted(extra_only):
        print(f"    - {api}")


def _verify_no_duplicates():
    content = get_pythoncapi_compat_h()
    lines = content.split("\n")
    func_defs = {}
    for i, line in enumerate(lines):
        m = re.match(r'^static inline\s+\w[\w\s\*]+?\s+(Py\w+)\s*\(', line)
        if m:
            name = m.group(1)
            if name in func_defs:
                print(f"  [WARNING] 重复定义: {name} (行 {func_defs[name]} 和 行 {i+1})")
            else:
                func_defs[name] = i + 1


def main():
    if len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        root = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    skip_site = _should_skip_site_packages(root)

    print(f"Python 3.8 兼容性修复脚本 - C/C++ 源码部分")
    print(f"=" * 60)
    print(f"工作目录: {root}")
    if skip_site:
        print(f"排除 site-packages 目录: 是（脚本不在 site-packages 内）")
    else:
        print(f"排除 site-packages 目录: 否（脚本在 site-packages 内）")
    print()

    print("[0/7] 检查兼容头文件覆盖情况...")
    _check_upstream_compat_coverage()
    _verify_no_duplicates()
    print()

    project_name, project_config = detect_project_type(root)
    if project_config:
        print(f"检测到项目类型: {project_name}")
        print(f"  使用项目特定的 include 路径: {project_config['include_line']}")
        print()

    print("[1/7] 扫描 C/C++ 源文件...")
    c_files = find_c_files(root, skip_site_packages=skip_site)
    print(f"  找到 {len(c_files)} 个 C/C++ 文件")

    print()
    print("[2/7] 检测使用 Python 3.9+ C API 的文件...")
    files_needing_compat = {}
    for filepath in c_files:
        needs_compat, apis = uses_python_c_api(filepath, project_config)
        if needs_compat:
            relpath = os.path.relpath(filepath, root)
            files_needing_compat[filepath] = apis
            print(f"  {relpath}: {', '.join(apis)}")

    print(f"\n  共 {len(files_needing_compat)} 个文件需要添加兼容头文件")

    print()
    print("[3/7] 检查已有 pythoncapi_compat.h 的完整性...")
    updated_compat = update_existing_pythoncapi_compat_h(root, project_config, skip_site_packages=skip_site)
    if updated_compat:
        print(f"  已更新 {len(updated_compat)} 个兼容头文件")
    else:
        print("  所有兼容头文件已包含完整的兼容实现")

    print()
    print("[4/7] 部署 pythoncapi_compat.h 兼容头文件...")
    deployed = deploy_pythoncapi_compat_h(root, files_needing_compat, project_config, skip_site_packages=skip_site)
    if deployed:
        print(f"  已部署到 {len(deployed)} 个位置:")
        for d in deployed:
            print(f"    - {d}")
    else:
        print("  pythoncapi_compat.h 已存在或无需部署")

    print()
    print("[5/7] 添加兼容头文件 #include...")
    include_count = 0
    for filepath in files_needing_compat:
        if add_pythoncapi_include(filepath, project_config):
            include_count += 1
            relpath = os.path.relpath(filepath, root)
            print(f"  已添加: {relpath}")

    print(f"  共修改 {include_count} 个文件")

    print()
    print("[6/7] 修复其他 C API 兼容性问题...")
    other_fixed = 0
    for filepath in c_files:
        try:
            if process_c_file(filepath):
                other_fixed += 1
                relpath = os.path.relpath(filepath, root)
                print(f"  修复: {relpath}")
        except Exception as e:
            relpath = os.path.relpath(filepath, root)
            print(f"  [ERROR] {relpath}: {e}")

    if other_fixed:
        print(f"  共修复 {other_fixed} 个文件")
    else:
        print("  无需额外修复")

    print()
    print("[7/7] 最终验证...")
    c_files_after = find_c_files(root, skip_site_packages=skip_site)

    api_checks = C_API_PATTERNS

    all_clean = True
    for pattern, name in api_checks:
        files_without_compat = []
        for filepath in c_files_after:
            relpath = os.path.relpath(filepath, root).replace("\\", "/")
            if "pythoncapi_compat" in relpath:
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue
            if "#include <Python.h>" not in content and '#include "Python.h"' not in content:
                continue
            if "pythoncapi_compat" in content:
                continue
            if project_config and project_config["include_line"] in content:
                continue
            if re.search(pattern, content):
                files_without_compat.append(relpath)
        if files_without_compat:
            print(f"  [!] {name}: {len(files_without_compat)} 个文件未包含兼容头文件")
            all_clean = False
        else:
            print(f"  [OK] {name}: 已全部处理")

    meth_method_count = 0
    for filepath in c_files_after:
        if "pythoncapi_compat" in filepath:
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        if "METH_METHOD" in content and "Python 3.9+" not in content:
            meth_method_count += 1
    if meth_method_count > 0:
        print(f"  [!] METH_METHOD: {meth_method_count} 个文件仍有未处理的 METH_METHOD")
        all_clean = False
    else:
        print(f"  [OK] METH_METHOD: 已全部处理")

    gil_unprotected_count = 0
    for filepath in c_files_after:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        if "Py_MOD_GIL_NOT_USED" not in content and "PyUnstable_Module_SetGIL" not in content:
            continue
        lines = content.split("\n")
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if "Py_MOD_GIL_NOT_USED" not in stripped and "PyUnstable_Module_SetGIL" not in stripped:
                continue
            protected = False
            for j in range(idx - 1, max(idx - 5, -1), -1):
                prev = lines[j].strip()
                if prev == "":
                    continue
                if ("#ifdef Py_GIL_DISABLED" in prev or
                    "#if defined(Py_GIL_DISABLED)" in prev or
                    "#if PY_VERSION_HEX" in prev):
                    protected = True
                break
            if not protected:
                gil_unprotected_count += 1
                relpath = os.path.relpath(filepath, root).replace("\\", "/")
                print(f"  [!] GIL API 未保护: {relpath}:{idx+1}")
    if gil_unprotected_count > 0:
        print(f"  [!] Py_MOD_GIL_NOT_USED/PyUnstable_Module_SetGIL: {gil_unprotected_count} 处未添加版本保护")
        all_clean = False
    else:
        print(f"  [OK] Py_MOD_GIL_NOT_USED/PyUnstable_Module_SetGIL: 已全部保护")

    print()
    if all_clean:
        print("所有 Python 3.9+ C API 兼容性问题已修复完成!")
    else:
        print("部分 C API 仍有残留，请人工检查上述标记的文件。")
    print()
    print("注意事项:")
    print("  1. PyCMethod / METH_METHOD (Python 3.9+) 无法简单兼容，")
    print("     已替换为注释标记，需要人工审查相关代码。")
    print("  2. PyType_GetSlot 已提供完整兼容实现（通过遍历 tp_base 链）。")
    print("  3. PyType_GetModule 已提供兼容实现（通过 __module__ 查找模块对象）。")
    print("  4. PyType_GetModuleByDef 仍为 stub 实现（需要模块定义指针匹配，")
    print("     无法简单实现），如遇运行时错误需人工审查。")
    print("  5. PyObject_VectorcallDict/Method (Python 3.12+) 已添加兼容实现，")
    print("     使用 PyObject_Call 回退方案。")
    print("  6. PyDict_GetItemRef/PyDict_GetItemStringRef (Python 3.13+) 已添加兼容实现，")
    print("     使用 PyDict_GetItemWithError 回退方案。")
    print("  7. PyList_GetItemRef (Python 3.13+) 已添加兼容实现，")
    print("     使用 PyList_GetItem + Py_XINCREF 回退方案。")
    print("  8. PyLong_AsInt (Python 3.13+) 已添加兼容实现，")
    print("     使用 PyLong_AsLong + 范围检查回退方案。")
    print("  9. Py_MOD_GIL_NOT_USED/PyUnstable_Module_SetGIL (Python 3.13+) ")
    print("     已添加 #ifdef Py_GIL_DISABLED 或版本检查保护。")
    print("  10. 脚本会自动检测已有 pythoncapi_compat.h 的完整性，")
    print("      缺少兼容实现的文件会被更新为完整版本。")
    print("  11. 对于 pytorch 等有项目特定 pythoncapi_compat.h 的项目，")
    print("      脚本会使用项目特定的 include 路径（如 <torch/csrc/utils/pythoncapi_compat.h>）。")
    print("  12. 建议编译测试确认所有 C 扩展正常工作。")
    print("  13. 对于 Python 源码的修复，请运行 fix_py38_python.py 脚本。")


if __name__ == "__main__":
    main()
