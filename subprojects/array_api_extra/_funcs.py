from __future__ import annotations

import operator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._typing import Array, ModuleType

__all__ = ["at", "atleast_nd", "isclose"]


def isclose(a, b, /, *, rtol=1e-05, atol=1e-08, xp=None):
    if xp is None:
        import numpy as _np
        xp = _np
    a = xp.asarray(a)
    b = xp.asarray(b)
    return xp.abs(a - b) <= (atol + rtol * xp.abs(b))

_UNDEF = object()


class at:
    def __init__(self, x, idx=_UNDEF, /):
        self._x = x
        self._idx = idx

    def __getitem__(self, idx):
        if self._idx is not _UNDEF:
            raise ValueError("Index has already been set")
        return at(self._x, idx)

    def set(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = y
        return x

    def add(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = operator.iadd(x[idx], y)
        return x

    def subtract(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = operator.isub(x[idx], y)
        return x

    def multiply(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = operator.imul(x[idx], y)
        return x

    def divide(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = operator.itruediv(x[idx], y)
        return x

    def power(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = operator.ipow(x[idx], y)
        return x

    def min(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = xp.minimum(x[idx], y)
        return x

    def max(self, y, /, copy=None, xp=None):
        x, idx = self._x, self._idx
        if idx is _UNDEF:
            raise ValueError("Index has not been set.")
        if xp is None:
            import numpy as _np
            xp = _np
        if copy or (copy is None and not _is_writeable(x)):
            x = xp.asarray(x, copy=True)
        x[idx] = xp.maximum(x[idx], y)
        return x


def _is_writeable(x):
    try:
        return x.flags.writeable
    except AttributeError:
        return False


def atleast_nd(x: Array, *, ndim: int, xp: ModuleType) -> Array:
    """
    Recursively expand the dimension of an array to at least `ndim`.

    Parameters
    ----------
    x : array
    ndim : int
        The minimum number of dimensions for the result.
    xp : array_namespace
        The standard-compatible namespace for `x`.

    Returns
    -------
    res : array
        An array with ``res.ndim`` >= `ndim`.
        If ``x.ndim`` >= `ndim`, `x` is returned.
        If ``x.ndim`` < `ndim`, `x` is expanded by prepending new axes
        until ``res.ndim`` equals `ndim`.

    Examples
    --------
    >>> import array_api_strict as xp
    >>> import array_api_extra as xpx
    >>> x = xp.asarray([1])
    >>> xpx.atleast_nd(x, ndim=3, xp=xp)
    Array([[[1]]], dtype=array_api_strict.int64)

    >>> x = xp.asarray([[[1, 2],
    ...                  [3, 4]]])
    >>> xpx.atleast_nd(x, ndim=1, xp=xp) is x
    True

    """
    if x.ndim < ndim:
        x = xp.expand_dims(x, axis=0)
        x = atleast_nd(x, ndim=ndim, xp=xp)
    return x
