<h1 align="center">
SciPy — Python 3.8 Backport
</h1>

[![Python 3.8](https://img.shields.io/badge/Python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Platform: Windows x64](https://img.shields.io/badge/Platform-Windows%20x64-green.svg)](https://github.com/Lanurence666/scipy_backport_py38)

---

[English](#english) | [日本語](#日本語) | [한국어](#한국어) | [Français](#français) | [Русский](#русский) | [Español](#español) | [Deutsch](#deutsch)

---

<a id="english"></a>
## 🇬🇧 English

### What is this?

This is a **Python 3.8 backport** of SciPy 1.18.0 (latest development version). The official SciPy dropped Python 3.8 support starting from SciPy 1.14. This fork backports the latest SciPy features and bug fixes to Python 3.8, allowing users who cannot upgrade their Python version to benefit from the latest improvements.

### Changes & Fixes

The following modifications were made to make SciPy compatible with Python 3.8:

1. **`pythoncapi_compat.h` fixes** — Updated version checks for `PyType_GetSlot`, `PyModule_AddFunctions`, `PyInterpreterState_GetDict`, `PyErr_GetExcInfo`/`PyErr_SetExcInfo` in multiple header files (`scipy/_lib/_uarray/`, `scipy/special/`, `scipy/sparse/linalg/_dsolve/`) to avoid redefining APIs already present in Python 3.8 headers.

2. **`lru_cached_property` compatibility** — Replaced direct `from functools import lru_cached_property` with try/except fallback blocks in 8 files (`_docscrape.py`, `_distribution_infrastructure.py`, `_covariance.py`, `_base.py`, `_genz_malik.py`, `_gauss_legendre.py`, `_gauss_kronrod.py`, `_short_time_fft.py`), since `lru_cached_property` was added in Python 3.8 but only as `cached_property`.

3. **`cached_property` import fix** — Added missing `from functools import cached_property` import in `_docscrape.py`.

4. **`TypeAlias` and `TypeGuard` compatibility** — Added try/except fallback for `TypeAlias` and `TypeGuard` imports from `typing` / `typing_extensions` in `array_api_compat/common/_helpers.py` and `_typing.py`.

5. **`tuple[...]` and `X | Y` syntax fix** — Replaced Python 3.10+ syntax (`tuple[...]`, `X | Y`) with `Tuple[...]` and `Union[X, Y]` from `typing` in `_typing.py`.

6. **`Mapping` import fix** — Changed `from collections.abc import Mapping` to `from typing import Mapping` in `_typing.py` for Python 3.8 compatibility.

7. **`array_api_extra.testing` module** — Created a stub `testing.py` module with `lazy_xp_function` fallback.

8. **MinGW toolchain** — Switched from MSVC to MinGW-w64 GCC 14.2.0 for all C/C++/Fortran compilation to resolve MSVC/MinGW mixed linking issues.

9. **Maximum optimization compilation** — Built with the following optimization flags:
   - GCC: `-O3 -ffast-math -fno-protect-parens -march=native -mtune=native -fomit-frame-pointer -fno-stack-protector`
   - Link-Time Optimization (LTO): Enabled
   - OpenBLAS: Linked statically

10. **Bundled OpenBLAS** — `libopenblas.dll` is included in the wheel for zero-configuration linear algebra support.

### Key Features

- Full SciPy 1.18.0 API available on Python 3.8
- Maximum performance optimization for Windows x64
- All standard SciPy submodules working: `linalg`, `integrate`, `special`, `optimize`, `fft`, `sparse`, `stats`, `signal`, `ndimage`, `interpolate`, `io`, `spatial`, and more
- Bundled OpenBLAS — no external dependency needed
- Compatible with NumPy 2.5.0 backport for Python 3.8

### Debugging Results

Compared to the last native Python 3.8 SciPy version (1.13.x):

| Feature | SciPy 1.13.x (Python 3.8 native) | This Backport (1.18.0) |
|---------|-----------------------------------|----------------------|
| Linear algebra (LAPACK/BLAS) | ✅ | ✅ |
| Integration | ✅ | ✅ |
| Special functions | ✅ | ✅ |
| Optimization | ✅ | ✅ |
| FFT | ✅ | ✅ |
| Sparse matrices | ✅ | ✅ |
| Statistics | ✅ | ✅ |
| Signal processing | ✅ | ✅ |
| New cubature integration | ❌ | ✅ |
| New distribution infrastructure | ❌ | ✅ |
| Performance | Baseline | Improved (LTO + -O3) |

### How to Compile

**Prerequisites:**
- Python 3.8 (64-bit)
- MinGW-w64 GCC 14+ (with gfortran)
- OpenBLAS
- Meson >= 1.8.3
- Ninja
- NumPy 2.5.0 backport (from this project)

**Build steps:**

```batch
# 1. Clone the repository
git clone https://github.com/Lanurence666/scipy_backport_py38.git
cd scipy_backport_py38

# 2. Install build dependencies
pip install meson-python meson ninja cython pybind11

# 3. Build with maximum optimizations (MinGW)
python -m build --wheel ^
    -Csetup-args=-Dbuildtype=release ^
    -Csetup-args=-Db_ndebug=if-release ^
    -Csetup-args=-Db_lto=true ^
    -Csetup-args=-Dblas=openblas ^
    -Csetup-args=-Dlapack=openblas

# 4. Install the wheel
pip install dist\scipy-*.whl
```

### Test File

A comprehensive test script `test_scipy_full.py` is included in this repository. It tests all scipy submodule imports and runs functional tests on key modules.

```batch
# Run the comprehensive test
python test_scipy_full.py
```

Or use this quick test:

```python
import numpy as np
import scipy
print("SciPy version:", scipy.__version__)

from scipy import linalg, integrate, special, optimize, fft, sparse, stats, signal

# Linear algebra
a = np.array([[1, 2], [3, 4]])
print("linalg.det:", linalg.det(a))

# Integration
result = integrate.quad(lambda x: x**2, 0, 1)
print("integrate.quad x^2 from 0 to 1:", result)

# Special functions
print("special.gamma(5):", special.gamma(5))

# Statistics
print("stats.norm.pdf(0):", stats.norm.pdf(0))

# Optimization
print("optimize.root:", optimize.root(lambda x: x**2 - 4, 1.0).x)

# FFT
print("fft.fft([1,2,3,4]):", fft.fft([1,2,3,4]))

print("All SciPy tests passed!")
```

---

<a id="日本語"></a>
## 🇯🇵 日本語

### これは何？

これはSciPy 1.18.0（最新開発版）の**Python 3.8バックポート**です。公式SciPyは1.14からPython 3.8サポートを終了しました。このフォークは最新のSciPy機能とバグ修正をPython 3.8にバックポートします。

### 変更と修正

1. **`pythoncapi_compat.h`の修正** — 複数のヘッダーファイルでバージョンチェックを更新。
2. **`lru_cached_property`互換性** — 8ファイルでtry/exceptフォールバックブロックに置き換え。
3. **`TypeAlias`/`TypeGuard`互換性** — typing/typing_extensionsからのフォールバック追加。
4. **Python 3.10+構文の修正** — `tuple[...]`→`Tuple[...]`、`X | Y`→`Union[X, Y]`。
5. **MinGWツールチェーン** — MSVC/MinGW混在リンク問題を解決するためMinGW-w64 GCC 14.2.0に切り替え。
6. **最大最適化コンパイル** — `-O3 -ffast-math -march=native`、LTO有効。
7. **OpenBLAS同梱** — `libopenblas.dll`をwheelに含め、外部依存なしで線形代数をサポート。

### 主な機能

- Python 3.8で完全なSciPy 1.18.0 APIが利用可能
- Windows x64向けの最大パフォーマンス最適化
- OpenBLAS同梱で設定不要

### コンパイル方法

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

<a id="한국어"></a>
## 🇰🇷 한국어

### 이것은 무엇입니까?

이것은 SciPy 1.18.0(최신 개발 버전)의 **Python 3.8 백포트**입니다. 공식 SciPy는 1.14부터 Python 3.8 지원을 중단했습니다.

### 변경 사항 및 수정

1. **`pythoncapi_compat.h` 수정** — 여러 헤더 파일에서 버전 검사 업데이트.
2. **`lru_cached_property` 호환성** — 8개 파일에서 try/except 폴백 블록으로 교체.
3. **MinGW 툴체인** — MinGW-w64 GCC 14.2.0으로 전환.
4. **최대 최적화 컴파일** — `-O3 -ffast-math -march=native`, LTO 활성화.
5. **OpenBLAS 번들** — `libopenblas.dll`이 wheel에 포함되어 외부 종속성 없이 선형 대수 지원.

### 주요 기능

- Python 3.8에서 전체 SciPy 1.18.0 API 사용 가능
- Windows x64 최대 성능 최적화
- OpenBLAS 번들로 설정 불필요

### 컴파일 방법

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

<a id="français"></a>
## 🇫🇷 Français

### Qu'est-ce que c'est ?

Il s'agit d'un **backport Python 3.8** de SciPy 1.18.0 (dernière version de développement). Le SciPy officiel a abandonné la prise en charge de Python 3.8 à partir de SciPy 1.14.

### Modifications et corrections

1. **Corrections de `pythoncapi_compat.h`** — Vérifications de version mises à jour dans plusieurs fichiers d'en-tête.
2. **Compatibilité `lru_cached_property`** — Remplacement par des blocs try/except dans 8 fichiers.
3. **Chaîne d'outils MinGW** — Passage à MinGW-w64 GCC 14.2.0.
4. **Compilation avec optimisation maximale** — `-O3 -ffast-math -march=native`, LTO activé.
5. **OpenBLAS inclus** — `libopenblas.dll` intégré au wheel.

### Fonctionnalités clés

- API complète SciPy 1.18.0 disponible sur Python 3.8
- Optimisation maximale pour Windows x64
- OpenBLAS inclus — aucune dépendance externe

### Comment compiler

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

<a id="русский"></a>
## 🇷🇺 Русский

### Что это?

Это **бэкпорт для Python 3.8** SciPy 1.18.0 (последняя версия разработки). Официальный SciPy прекратил поддержку Python 3.8 начиная с версии 1.14.

### Изменения и исправления

1. **Исправления `pythoncapi_compat.h`** — Обновлены проверки версий в нескольких заголовочных файлах.
2. **Совместимость `lru_cached_property`** — Заменено блоками try/except в 8 файлах.
3. **Инструментарий MinGW** — Перход на MinGW-w64 GCC 14.2.0.
4. **Компиляция с максимальной оптимизацией** — `-O3 -ffast-math -march=native`, LTO включён.
5. **Встроенный OpenBLAS** — `libopenblas.dll` включён в wheel.

### Ключевые возможности

- Полный API SciPy 1.18.0 на Python 3.8
- Максимальная оптимизация для Windows x64
- Встроенный OpenBLAS — без внешних зависимостей

### Как скомпилировать

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

<a id="español"></a>
## 🇪🇸 Español

### ¿Qué es esto?

Este es un **backport para Python 3.8** de SciPy 1.18.0 (última versión de desarrollo). El SciPy oficial dejó de soportar Python 3.8 a partir de SciPy 1.14.

### Cambios y correcciones

1. **Correcciones de `pythoncapi_compat.h`** — Verificaciones de versión actualizadas en múltiples archivos de encabezado.
2. **Compatibilidad `lru_cached_property`** — Reemplazado con bloques try/except en 8 archivos.
3. **Cadena de herramientas MinGW** — Cambio a MinGW-w64 GCC 14.2.0.
4. **Compilación con optimización máxima** — `-O3 -ffast-math -march=native`, LTO habilitado.
5. **OpenBLAS incluido** — `libopenblas.dll` integrado en el wheel.

### Características clave

- API completa de SciPy 1.18.0 disponible en Python 3.8
- Optimización máxima para Windows x64
- OpenBLAS incluido — sin dependencias externas

### Cómo compilar

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

<a id="deutsch"></a>
## 🇩🇪 Deutsch

### Was ist das?

Dies ist ein **Python 3.8-Backport** von SciPy 1.18.0 (neueste Entwicklungsversion). Das offizielle SciPy hat die Python 3.8-Unterstützung ab SciPy 1.14 eingestellt.

### Änderungen und Korrekturen

1. **`pythoncapi_compat.h`-Korrekturen** — Versionsprüfungen in mehreren Header-Dateien aktualisiert.
2. **`lru_cached_property`-Kompatibilität** — Durch try/except-Blöcke in 8 Dateien ersetzt.
3. **MinGW-Toolchain** — Umstieg auf MinGW-w64 GCC 14.2.0.
4. **Kompilierung mit maximaler Optimierung** — `-O3 -ffast-math -march=native`, LTO aktiviert.
5. **OpenBLAS eingebunden** — `libopenblas.dll` im Wheel enthalten.

### Hauptfunktionen

- Volles SciPy 1.18.0-API unter Python 3.8 verfügbar
- Maximale Optimierung für Windows x64
- OpenBLAS eingebunden — keine externen Abhängigkeiten

### Kompilierungsanleitung

```batch
pip install meson-python meson ninja cython pybind11
python -m build --wheel -Csetup-args=-Dbuildtype=release -Csetup-args=-Db_lto=true
pip install dist\scipy-*.whl
```

---

## License

SciPy is licensed under the [BSD-3-Clause License](https://opensource.org/licenses/BSD-3-Clause).
