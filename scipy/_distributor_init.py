""" Distributor init file

Distributors: you can replace the contents of this file with your own custom
code to support particular distributions of SciPy.

For example, this is a good place to put any checks for hardware requirements
or BLAS/LAPACK library initialization.

The SciPy standard source distribution will not put code in this file beyond
the try-except import of `_distributor_init_local` (which is not part of a
standard source distribution), so you can safely replace this file with your
own version.
"""

import os as _os
import sys as _sys

_scipy_dir = _os.path.dirname(_os.path.abspath(__file__))
_libopenblas = _os.path.join(_scipy_dir, 'libopenblas.dll')

if _os.path.isfile(_libopenblas):
    if hasattr(_os, 'add_dll_directory'):
        _os.add_dll_directory(_scipy_dir)
    _os.environ.setdefault('PATH', '')
    _os.environ['PATH'] = _scipy_dir + _os.pathsep + _os.environ['PATH']

del _os, _sys, _scipy_dir, _libopenblas

try:
    from . import _distributor_init_local  # noqa: F401
except ImportError:
    pass
