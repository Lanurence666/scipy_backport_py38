#!/usr/bin/env python3
"""
SciPy Python 3.8 Backport Test Script
======================================
Tests all scipy submodules for import correctness and runs basic
functional tests on key modules to verify the backport works properly.

Usage:
    python test_scipy_full.py
"""

import sys
import io


def test_submodule_imports():
    import scipy
    import pkgutil
    import importlib

    print(f"scipy version: {scipy.__version__}")
    print(f"scipy location: {scipy.__file__}")
    print()

    modules = [
        "scipy.cluster", "scipy.cluster.hierarchy", "scipy.cluster.vq",
        "scipy.constants", "scipy.datasets", "scipy.fft", "scipy.fftpack",
        "scipy.integrate", "scipy.interpolate", "scipy.io", "scipy.io.arff",
        "scipy.io.harwell_boeing", "scipy.io.idl", "scipy.io.matlab",
        "scipy.io.netcdf", "scipy.io.wavfile", "scipy.linalg",
        "scipy.linalg.blas", "scipy.linalg.lapack", "scipy.linalg.interpolative",
        "scipy.misc", "scipy.ndimage", "scipy.odr", "scipy.optimize",
        "scipy.signal", "scipy.signal.windows", "scipy.sparse",
        "scipy.sparse.csgraph", "scipy.sparse.linalg", "scipy.spatial",
        "scipy.spatial.distance", "scipy.spatial.transform", "scipy.special",
        "scipy.stats", "scipy.stats.contingency", "scipy.stats.distributions",
        "scipy.stats.mstats", "scipy.stats.qmc", "scipy.stats.sampling",
    ]

    print("--- Submodule Import Tests ---")
    failed = []
    passed = 0
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"  OK: {mod}")
            passed += 1
        except Exception as e:
            err = str(e)[:150]
            print(f"  FAIL: {mod} -> {err}")
            failed.append((mod, err))

    print(f"\nSubmodule Import: {passed}/{len(modules)} passed")
    return failed


def test_functional():
    import numpy as np

    print("\n--- Functional Tests ---")
    results = []

    tests = [
        ("integrate.quad", _test_integrate),
        ("linalg.det", _test_linalg),
        ("linalg.svd", _test_linalg_svd),
        ("optimize.minimize", _test_optimize),
        ("signal.butter", _test_signal),
        ("stats.ttest_ind", _test_stats),
        ("stats.Normal", _test_stats_normal),
        ("fft.fft", _test_fft),
        ("interpolate.interp1d", _test_interpolate),
        ("ndimage.gaussian_filter", _test_ndimage),
        ("sparse.csr_matrix", _test_sparse),
        ("special.gamma", _test_special),
        ("spatial.transform.Rotation", _test_rotation),
        ("io.savemat/loadmat", _test_io),
        ("odr.ODR", _test_odr),
        ("constants.c", _test_constants),
        ("datasets", _test_datasets),
        ("fftpack.fft", _test_fftpack),
    ]

    for name, fn in tests:
        try:
            fn()
            print(f"  OK: {name}")
            results.append((name, True))
        except Exception as e:
            err = str(e)[:150]
            print(f"  FAIL: {name} -> {err}")
            results.append((name, False))

    passed = sum(1 for _, ok in results if ok)
    print(f"\nFunctional Tests: {passed}/{len(results)} passed")
    return results


def _test_integrate():
    from scipy import integrate
    result = integrate.quad(lambda x: x**2, 0, 1)
    assert abs(result[0] - 1/3) < 1e-6, f"Expected ~0.333333, got {result[0]}"


def _test_linalg():
    from scipy import linalg
    import numpy as np
    A = np.array([[1, 2], [3, 4]])
    det = linalg.det(A)
    assert abs(det - (-2.0)) < 1e-6, f"Expected -2.0, got {det}"


def _test_linalg_svd():
    from scipy import linalg
    import numpy as np
    A = np.array([[1, 2], [3, 4]], dtype=float)
    u, s, vh = linalg.svd(A)
    assert len(s) == 2, f"Expected 2 singular values, got {len(s)}"


def _test_optimize():
    from scipy import optimize
    result = optimize.minimize(lambda x: (x[0]-1)**2 + (x[1]-2)**2, [0, 0])
    assert result.success, f"Optimization failed: {result.message}"
    assert abs(result.x[0] - 1.0) < 1e-4, f"Expected x[0]~1.0, got {result.x[0]}"
    assert abs(result.x[1] - 2.0) < 1e-4, f"Expected x[1]~2.0, got {result.x[1]}"


def _test_signal():
    from scipy import signal
    b, a = signal.butter(4, 0.1)
    assert len(b) == 5, f"Expected 5 coefficients, got {len(b)}"


def _test_stats():
    from scipy import stats
    t_stat, p_val = stats.ttest_ind([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    assert abs(t_stat) < 5, f"t-statistic out of range: {t_stat}"


def _test_stats_normal():
    from scipy.stats import Normal
    d = Normal()
    assert abs(d.mean()) < 1e-6, f"Expected mean=0, got {d.mean()}"


def _test_fft():
    from scipy import fft
    import numpy as np
    y = fft.fft(np.array([1, 2, 3, 4]))
    assert len(y) == 4, f"Expected 4 values, got {len(y)}"


def _test_interpolate():
    from scipy import interpolate
    f = interpolate.interp1d([0, 1, 2, 3, 4], [0, 1, 4, 9, 16])
    val = f(1.5)
    assert 1.0 < val < 4.0, f"Interpolation result out of range: {val}"


def _test_ndimage():
    from scipy import ndimage
    import numpy as np
    arr = np.zeros((5, 5))
    arr[2, 2] = 1
    filtered = ndimage.gaussian_filter(arr, sigma=1)
    assert filtered.sum() > 0, "Gaussian filter result is all zeros"


def _test_sparse():
    from scipy import sparse
    import numpy as np
    mat = sparse.csr_matrix(np.eye(3))
    assert mat.nnz == 3, f"Expected 3 non-zeros, got {mat.nnz}"


def _test_special():
    from scipy import special
    val = special.gamma(5)
    assert abs(val - 24.0) < 1e-6, f"Expected 24.0, got {val}"


def _test_rotation():
    from scipy.spatial.transform import Rotation
    r = Rotation.identity()
    assert r is not None, "Failed to create Rotation"


def _test_io():
    from scipy import io
    import numpy as np
    import tempfile
    import os
    data = {"array": np.array([1, 2, 3])}
    with tempfile.NamedTemporaryFile(suffix=".mat", delete=False) as f:
        fname = f.name
    try:
        io.savemat(fname, data)
        loaded = io.loadmat(fname)
        assert "array" in loaded, "Key 'array' not found in loaded data"
    finally:
        os.unlink(fname)


def _test_odr():
    from scipy import odr
    import numpy as np

    def linear_func(B, x):
        return B[0] * x + B[1]

    model = odr.Model(linear_func)
    x = np.array([0, 1, 2, 3, 4])
    y = np.array([0.1, 1.0, 2.1, 2.9, 4.0])
    data = odr.Data(x, y)
    odr_obj = odr.ODR(data, model, beta0=[1.0, 0.0])
    output = odr_obj.run()
    assert abs(output.beta[0] - 1.0) < 0.5, f"Unexpected slope: {output.beta[0]}"


def _test_constants():
    from scipy import constants
    assert abs(constants.c - 299792458) < 1, f"Speed of light incorrect: {constants.c}"


def _test_datasets():
    from scipy import datasets
    try:
        ascent = datasets.ascent()
        assert ascent is not None, "Failed to load ascent dataset"
        assert ascent.size > 0, "Dataset is empty"
    except ImportError:
        print("    (skipped: pooch not installed)")


def _test_fftpack():
    from scipy import fftpack
    import numpy as np
    y = fftpack.fft(np.array([1, 2, 3, 4]))
    assert len(y) == 4, f"Expected 4 values, got {len(y)}"


def main():
    print("=" * 60)
    print("SciPy Python 3.8 Backport - Comprehensive Test")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print()

    import_failed = test_submodule_imports()
    func_results = test_functional()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if not import_failed and all(ok for _, ok in func_results):
        print("ALL TESTS PASSED!")
        return 0
    else:
        if import_failed:
            print(f"  {len(import_failed)} module import(s) failed")
        func_failed = sum(1 for _, ok in func_results if not ok)
        if func_failed:
            print(f"  {func_failed} functional test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
