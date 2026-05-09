#!/usr/bin/env python3
"""
Python 3.8 兼容性修复脚本 - Python 源码部分
============================================

将此脚本放在项目源码根目录下运行，自动修复所有 Python 3.9+ 语法和 API，
使项目源码兼容 Python 3.8。

修复内容:
  1. PEP 585 - 内置泛型 (list[X], dict[K,V], tuple[X,Y], set[X] 等)
  2. PEP 604 - 联合类型 (X | Y 在类型注解中)
  3. PEP 584 - 字典合并运算符 (d1 | d2 → {**d1, **d2}, d1 |= d2 → d1.update(d2))
  4. PEP 616 - str.removeprefix() / str.removesuffix() (Python 3.9+)
  5. PEP 593 - typing.Annotated → try/except 回退 typing_extensions
  6. functools.cache → functools.lru_cache(maxsize=None) (Python 3.9+)
  7. import importlib.metadata → try/except 回退 importlib_metadata
  8. from importlib.metadata import → try/except 回退 importlib_metadata
  9. from importlib import metadata → try/except 回退 importlib_metadata
 10. from typing import TypeAlias/TypeGuard/ParamSpec/Concatenate → try/except 回退 typing_extensions
 11. isinstance(x, A | B) / issubclass(x, A | B) → isinstance(x, (A, B)) / issubclass(x, (A, B)) (Python 3.10+)
 12. zoneinfo → try/except 回退 backports.zoneinfo (Python 3.9+)
 13. graphlib → try/except 回退 (Python 3.9+)
 14. math.lcm() → try/except 回退兼容实现 (Python 3.9+)
 15. math.nextafter() / math.ulp() → try/except 回退兼容实现 (Python 3.9+)
 16. collections.XXX (Mapping, Iterable 等) → collections.abc.XXX (Python 3.9+ 弃用)
 17. random.randbytes() → try/except 回退兼容实现 (Python 3.9+)
 18. ast.unparse() → try/except 回退 astunparse (Python 3.9+)
 19. bytes/bytearray.removeprefix/removesuffix → 运行时 monkey-patch 兼容 (Python 3.9+)
 20. PEP 572 - 括号化上下文管理器 (with (expr as var): → with expr as var:) (Python 3.10+)
 21. setup.py / pyproject.toml 中的 Python 版本约束
 22. zip(..., strict=True) → _zip_strict() 回退兼容实现 (Python 3.10+)
 23. int.bit_count() → _int_bit_count() 回退兼容实现 (Python 3.10+)
 24. aiter() / anext() → _aiter_compat() / _anext_compat() 回退 (Python 3.10+)
 25. bisect 模块 key= 参数 → 兼容实现回退 (Python 3.10+)
 26. dataclass(slots=True) → 移除 slots 参数 (Python 3.10+)
 27. collections.abc.Callable[...] → typing.Callable[...] (Python 3.8 不支持下标)
 28. functools.lru_cached_property → try/except 回退兼容实现 (Python 3.9+)
 29. functools.cached_property → 自动添加缺失的导入 (Python 3.8+)
 30. types.GenericAlias/EllipsisType/NotImplementedType → __init__.py 中 monkey-patch (Python 3.9+)
 31. dict(...) | dict → 改进的字典合并检测，避免误替换 numpy 数组/集合的 | 操作

用法:
  python fix_py38_python.py [源码目录]

  如果不指定目录，默认在脚本所在目录下查找。

注意:
  - 此脚本会修改源文件，请先确保已备份或使用版本控制。
  - 运行后建议人工检查修改结果，特别是复杂的链式调用。
  - 对于 C/C++ 源码的修复，请使用 fix_py38_c.py 脚本。
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


def find_py_files(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))
    return py_files


def find_c_files(root, skip_site_packages=True):
    skip = SKIP_DIRS_NO_SITE if skip_site_packages else SKIP_DIRS
    c_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f.endswith((".c", ".h", ".cpp", ".hpp")):
                c_files.append(os.path.join(dirpath, f))
    return c_files


# ============================================================
# 修复函数
# ============================================================

def fix_pep695_generic_class(content):
    if not re.search(r"^class\s+\w+\[", content, re.MULTILINE):
        return content

    generic_names = set()

    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\s*)class\s+(\w+)\[([^\]]+)\]\s*(?:\(([^)]*)\))?\s*:', line)
        if m:
            indent = m.group(1) or ""
            name = m.group(2)
            type_params_str = m.group(3)
            bases = m.group(4) or ""

            has_unpack = bool(re.search(r'\*\w+', type_params_str))

            if has_unpack:
                class_end = i + 1
                for k in range(i + 1, len(lines)):
                    if lines[k].strip() == "":
                        continue
                    if not lines[k].startswith(indent + " ") and not lines[k].startswith(indent + "\t"):
                        class_end = k
                        break
                    class_end = k + 1
                else:
                    class_end = len(lines)

                new_lines.append(f"{indent}# TODO: Python 3.8 compat - PEP 695 generic class with TypeVarTuple/ParamSpec needs manual conversion")
                for k in range(i, min(class_end, len(lines))):
                    if lines[k].strip():
                        new_lines.append("# " + lines[k])
                    else:
                        new_lines.append(lines[k])
                i = class_end
                continue

            type_params = []
            for tp in re.split(r",\s*", type_params_str):
                tp = tp.strip()
                if ":" in tp:
                    tp_name = tp.split(":")[0].strip()
                elif "=" in tp:
                    tp_name = tp.split("=")[0].strip()
                else:
                    tp_name = tp.strip()
                type_params.append(tp_name)

            generic_names.add((name, tuple(type_params)))

            if bases:
                if "Protocol" in bases:
                    new_bases = bases.replace("Protocol", f"Protocol, Generic[{', '.join(type_params)}]")
                else:
                    new_bases = f"{bases}, Generic[{', '.join(type_params)}]"
            else:
                new_bases = f"Generic[{', '.join(type_params)}]"

            new_lines.append(f"{indent}class {name}({new_bases}):")
            i += 1
            continue

        new_lines.append(line)
        i += 1

    content = '\n'.join(new_lines)

    if generic_names:
        has_generic_import = False
        for line in content.split("\n"):
            if re.match(r"^from typing import", line) and "Generic" in line:
                has_generic_import = True
                break

        if not has_generic_import:
            m = re.search(r"^from typing import (.+)$", content, re.MULTILINE)
            if m:
                imports = [x.strip() for x in m.group(1).split(",")]
                if "Generic" not in imports:
                    imports.append("Generic")
                content = re.sub(
                    r"^from typing import .+$",
                    f"from typing import {', '.join(imports)}",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content = re.sub(
                    r"^(from __future__ import annotations\n)",
                    r"\1from typing import Generic\n",
                    content,
                )

    return content


def fix_lambda_decorator(content):
    if not re.search(r'^\s*@lambda\b', content, re.MULTILINE):
        return content

    deferred_decorators = []

    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\s*)@lambda\s+(\w+)\s*:\s*(.+)$', line)
        if m:
            indent = m.group(1)
            param_name = m.group(2)
            decorator_body = m.group(3).strip()

            other_decorators = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_m = re.match(r'^(\s*)@', next_line)
                if next_m:
                    other_decorators.append(next_line)
                    j += 1
                    continue
                break

            if j < len(lines):
                func_line = lines[j]
                func_m = re.match(r'^(\s*)(async\s+)?def\s+(\w+)\s*\(', func_line)
                if func_m:
                    func_indent = func_m.group(1)
                    func_name = func_m.group(3)

                    for d in other_decorators:
                        new_lines.append(d)

                    new_lines.append(func_line)

                    class_m = None
                    for k in range(len(new_lines) - 1, -1, -1):
                        cm = re.match(r'^(\s*)class\s+(\w+)', new_lines[k])
                        if cm:
                            class_m = cm
                            break

                    if class_m:
                        class_name = class_m.group(2)
                        wrapper_call = decorator_body.replace(param_name, f"{class_name}.{func_name}")
                        deferred_decorators.append(f"{class_name}.{func_name} = {wrapper_call}")
                    else:
                        wrapper_call = decorator_body.replace(param_name, func_name)
                        deferred_decorators.append(f"{func_name} = {wrapper_call}")

                    i = j + 1
                    continue
                else:
                    new_lines.append(line)
                    i += 1
                    continue
            else:
                new_lines.append(line)
                i += 1
                continue

        new_lines.append(line)
        i += 1

    if deferred_decorators:
        for dd in deferred_decorators:
            new_lines.append(dd)

    return '\n'.join(new_lines)


def fix_pep695_generic_function(content):
    if not re.search(r"^(\s*)def\s+\w+\[", content, re.MULTILINE):
        return content

    typevar_defs = []

    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^(\s*)def\s+(\w+)\[([^\]]+)\]\s*\(([^)]*)\)\s*(.*?)\s*:', line)
        if m:
            indent = m.group(1) or ""
            name = m.group(2)
            type_params_str = m.group(3)
            params = m.group(4)
            return_info = m.group(5).strip()

            type_params = []
            for tp in re.split(r",\s*", type_params_str):
                tp = tp.strip()
                if ":" in tp:
                    tp_name = tp.split(":")[0].strip()
                elif "=" in tp:
                    tp_name = tp.split("=")[0].strip()
                else:
                    tp_name = tp.strip()
                type_params.append(tp_name)
                typevar_defs.append(f"{tp_name} = TypeVar('{tp_name}')")

            if return_info:
                new_lines.append(f"{indent}def {name}({params}) {return_info}:")
            else:
                new_lines.append(f"{indent}def {name}({params}):")

            i += 1
            continue

        new_lines.append(line)
        i += 1

    if typevar_defs:
        insert_pos = 0
        for idx, line in enumerate(new_lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                if not stripped.startswith('from ') and not stripped.startswith('import ') and not stripped.startswith('@'):
                    insert_pos = idx
                    break
                insert_pos = idx + 1

        for tv_def in typevar_defs:
            new_lines.insert(insert_pos, tv_def)
            insert_pos += 1

    content = '\n'.join(new_lines)

    if re.search(r"TypeVar", content) and not re.search(r"from typing import.*TypeVar", content):
        m = re.search(r"^from typing import (.+)$", content, re.MULTILINE)
        if m:
            old_line = m.group(0)
            imports = m.group(1)
            if "TypeVar" not in imports:
                new_imports = imports.rstrip() + ", TypeVar"
                content = content.replace(old_line, f"from typing import {new_imports}", 1)
        else:
            content = "from typing import TypeVar\n" + content

    return content


def fix_pep695_type_stmt(content):
    if not re.search(r"^type\s+\w+", content, re.MULTILINE):
        return content

    needs_typevar = False
    typevar_defs = []

    lines = content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        m = re.match(r"^(\s*)type\s+(\w+)\s*\[([^\]]+)\]\s*=\s*(.*)$", line)
        if m:
            indent = m.group(1)
            name = m.group(2)
            type_params_str = m.group(3)
            value = m.group(4).rstrip()

            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped == "" or stripped.startswith("#"):
                    break
                if stripped.startswith(("type ", "class ", "def ", "from ", "import ")):
                    break
                if lines[j].startswith(indent) and (stripped.startswith("|") or stripped.startswith("(")):
                    value += " " + stripped
                    j += 1
                else:
                    break

            type_params = []
            for tp in re.split(r",\s*", type_params_str):
                tp = tp.strip()
                if ":" in tp:
                    parts = tp.split(":", 1)
                    tp_name = parts[0].strip()
                    tp_bound = parts[1].strip()
                    typevar_defs.append(f"{indent}{tp_name} = TypeVar('{tp_name}', bound={tp_bound})")
                elif "=" in tp:
                    parts = tp.split("=", 1)
                    tp_name = parts[0].strip()
                    tp_default = parts[1].strip()
                    typevar_defs.append(f"{indent}{tp_name} = TypeVar('{tp_name}', default={tp_default})")
                else:
                    type_params.append(tp)
                    typevar_defs.append(f"{indent}{tp} = TypeVar('{tp}')")

            needs_typevar = True
            new_lines.append(f"{indent}{name}: TypeAlias = {value}")

            i = j
            continue

        m2 = re.match(r"^(\s*)type\s+(\w+)\s*=\s*(.*)$", line)
        if m2:
            indent = m2.group(1)
            name = m2.group(2)
            value = m2.group(3).rstrip()

            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped == "" or stripped.startswith("#"):
                    break
                if stripped.startswith(("type ", "class ", "def ", "from ", "import ")):
                    break
                if lines[j].startswith(indent) and (stripped.startswith("|") or stripped.startswith("(")):
                    value += " " + stripped
                    j += 1
                else:
                    break

            new_lines.append(f"{indent}{name}: TypeAlias = {value}")

            i = j
            continue

        new_lines.append(line)
        i += 1

    if typevar_defs:
        insert_idx = 0
        for k, l in enumerate(new_lines):
            if l.startswith("from ") or l.startswith("import "):
                insert_idx = k + 1
            elif l.strip() == "" and insert_idx > 0:
                continue
            elif not l.startswith("from ") and not l.startswith("import ") and not l.startswith("#") and l.strip() != "":
                break
        for tv_def in typevar_defs:
            new_lines.insert(insert_idx, tv_def)
            insert_idx += 1

    result = "\n".join(new_lines)

    needed_imports = set()
    if "TypeAlias" in result:
        needed_imports.add("TypeAlias")
    if needs_typevar:
        needed_imports.add("TypeVar")

    if needed_imports:
        has_typing_import = False
        for k, l in enumerate(result.split("\n")):
            m = re.match(r"^from typing import (.+)$", l)
            if m:
                has_typing_import = True
                imports = [x.strip() for x in m.group(1).split(",")]
                for imp in needed_imports:
                    if imp not in imports:
                        imports.append(imp)
                result = result.replace(l, f"from typing import {', '.join(imports)}")
                break
        if not has_typing_import:
            result_lines = result.split("\n")
            insert_pos = 0
            for k, l in enumerate(result_lines):
                if l.startswith("#!") or l.startswith("# -*-") or l.startswith("# vim:") or l.startswith("# coding:"):
                    insert_pos = k + 1
                elif l.startswith('"""') or l.startswith("'''"):
                    break
                elif l.strip() == "" or l.startswith("#"):
                    insert_pos = k + 1
                    continue
                else:
                    break
            result_lines.insert(insert_pos, f"from typing import {', '.join(sorted(needed_imports))}")
            result = "\n".join(result_lines)

    return result


def _find_matching_paren_in_line(line, start):
    depth = 0
    in_string = False
    string_char = None
    is_raw = False
    i = start
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == '\\' and not is_raw:
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if i + 1 < len(line) and ch in ('r', 'b', 'f', 'u') and line[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (ch == 'r')
            string_char = line[i + 1]
            i += 2
            continue
        if ch in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = ch
            i += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def fix_parenthesized_context_manager(content):
    if not re.search(r'with\s*\(', content):
        return content

    lines = content.split("\n")
    new_lines = _fix_paren_ctx_lines(lines)
    return "\n".join(new_lines)


def _fix_paren_ctx_lines(lines):
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m_prefix = re.match(r'^(\s*)with\s*\(', line)
        if not m_prefix:
            new_lines.append(line)
            i += 1
            continue

        indent = m_prefix.group(1)
        paren_start = line.index('(', len(indent) + len('with'))
        paren_end = _find_matching_paren_in_line(line, paren_start)

        if paren_end > 0:
            inner = line[paren_start + 1:paren_end].strip()
            rest = line[paren_end + 1:].strip()
            as_m = re.match(r'^as\s+(\w+)\s*:\s*$', rest)
            close_m = re.match(r'^:\s*$', rest)
            handled = False
            if as_m:
                var = as_m.group(1)
                if not _has_unbalanced_parens(inner):
                    inner = _clean_ctx_expr(inner)
                    new_lines.append(f"{indent}with {inner} as {var}:")
                    handled = True
            elif close_m:
                if not _has_unbalanced_parens(inner):
                    inner = _clean_ctx_expr(inner)
                    new_lines.append(f"{indent}with {inner}:")
                    handled = True
            if handled:
                i += 1
                continue
            new_lines.append(line)
            i += 1
            continue

        first_expr = line[paren_start + 1:].strip()
        collected = [first_expr] if first_expr else []
        full_line_comments = []
        inline_comments = []
        j = i + 1
        found_as = False
        as_var = None
        while j < len(lines):
            next_line = lines[j]
            stripped_next = next_line.strip()
            if stripped_next.startswith('#'):
                full_line_comments.append(next_line)
                j += 1
                continue
            expr_part_clean, trailing_comment = _strip_trailing_comment(stripped_next)
            as_m = re.match(r'^(.*?)\)\s*as\s+(\w+)\s*:\s*$', expr_part_clean)
            if as_m:
                as_var = as_m.group(2)
                ep = as_m.group(1).strip()
                if ep:
                    collected.append(ep)
                if trailing_comment:
                    inline_comments.append(trailing_comment)
                found_as = True
                j += 1
                break
            close_m = re.match(r'^(.*?)\)\s*:\s*$', expr_part_clean)
            if close_m:
                ep = close_m.group(1).strip()
                if ep:
                    collected.append(ep)
                if trailing_comment:
                    inline_comments.append(trailing_comment)
                j += 1
                break
            else:
                if expr_part_clean:
                    collected.append(expr_part_clean)
                if trailing_comment:
                    inline_comments.append(trailing_comment)
                j += 1

        if collected:
            expr = " ".join(collected).strip()
            expr = _clean_ctx_expr(expr)
            if not _has_unbalanced_parens(expr):
                for cl in full_line_comments:
                    new_lines.append(cl)
                trailing = "  " + "  ".join(inline_comments) if inline_comments else ""
                if found_as and as_var:
                    new_lines.append(f"{indent}with {expr} as {as_var}:{trailing}")
                else:
                    new_lines.append(f"{indent}with {expr}:{trailing}")
                i = j
                continue

        new_lines.append(line)
        i += 1

    return new_lines


def _has_unbalanced_parens(expr):
    depth = 0
    in_string = False
    string_char = None
    is_raw = False
    i = 0
    while i < len(expr):
        ch = expr[i]
        if in_string:
            if ch == '\\' and not is_raw:
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if i + 1 < len(expr) and expr[i] in ('r', 'b', 'f', 'u') and expr[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (expr[i] == 'r')
            string_char = expr[i + 1]
            i += 2
            continue
        if ch in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = ch
            i += 1
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
            if depth < 0:
                return True
        i += 1
    return depth != 0


def _strip_trailing_comment(line):
    in_string = False
    string_char = None
    is_raw = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == '\\' and not is_raw:
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if i + 1 < len(line) and ch in ('r', 'b', 'f', 'u') and line[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (ch == 'r')
            string_char = line[i + 1]
            i += 2
            continue
        if ch in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = ch
            i += 1
            continue
        if ch == '#':
            return line[:i].rstrip(), line[i:]
        i += 1
    return line, ""


def _has_ctx_manager_comma(expr):
    depth = 0
    in_string = False
    string_char = None
    is_raw = False
    i = 0
    while i < len(expr):
        ch = expr[i]
        if in_string:
            if ch == '\\' and not is_raw:
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if i + 1 < len(expr) and expr[i] in ('r', 'b', 'f', 'u') and expr[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (expr[i] == 'r')
            string_char = expr[i + 1]
            i += 2
            continue
        if ch in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = ch
            i += 1
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            return True
        i += 1
    return False


def _clean_ctx_expr(expr):
    expr = expr.strip()
    expr = re.sub(r'\s+', ' ', expr)
    expr = re.sub(r'\(\s+', '(', expr)
    expr = re.sub(r'\s+\)', ')', expr)
    expr = re.sub(r',\s*\)', ')', expr)
    if expr.endswith(","):
        expr = expr[:-1].strip()
    if expr.endswith(","):
        expr = expr[:-1].strip()
    return expr


def _find_match_blocks_regex(content):
    lines = content.split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        m = re.match(r'^(\s+)match\s+(.+):$', lines[i])
        if m:
            indent = m.group(1)
            start = i
            j = i + 1
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped == "":
                    j += 1
                    continue
                if not lines[j].startswith(indent + "    ") and not lines[j].startswith(indent + "\t"):
                    if re.match(r'^\s+case\s+', lines[j]):
                        j += 1
                        continue
                    break
                j += 1
            end = j - 1
            while end > start and lines[end].strip() == "":
                end -= 1
            class _MatchBlock:
                def __init__(self, lineno, end_lineno):
                    self.lineno = lineno
                    self.end_lineno = end_lineno
            blocks.append(_MatchBlock(start + 1, end + 1))
            i = j
        else:
            i += 1
    return blocks


def fix_match_case(content):
    if not re.search(r'^\s+match\s+\S.*:$', content, re.MULTILINE):
        return content

    if not re.search(r'^\s+case\s+', content, re.MULTILINE):
        return content

    import ast

    has_ast_match = hasattr(ast, 'Match')

    if has_ast_match:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content

        match_nodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Match):
                match_nodes.append(node)

        if not match_nodes:
            return content
    else:
        match_nodes = _find_match_blocks_regex(content)

    lines = content.split("\n")

    for match_node in sorted(match_nodes, key=lambda n: n.lineno, reverse=True):
        match_start = match_node.lineno - 1
        match_end = match_node.end_lineno - 1

        match_line = lines[match_start]
        m = re.match(r"^(\s+)match\s+(.*):$", match_line)
        if not m:
            continue

        match_indent = m.group(1)
        match_expr = m.group(2)
        if match_expr.endswith(":"):
            match_expr = match_expr[:-1]

        case_line_indices = []
        for k in range(match_start + 1, match_end + 1):
            if k < len(lines) and re.match(r"^\s+case\s+.+:$", lines[k]):
                case_line_indices.append(k)

        can_convert = True
        case_infos = []
        for case_line_idx in case_line_indices:
            case_line = lines[case_line_idx]
            case_m = re.match(r"^\s+case\s+(.+):$", case_line)
            if not case_m:
                can_convert = False
                break

            raw_pattern = case_m.group(1).strip()

            guard = None
            guard_match = re.match(r'^(.+?)\s+if\s+(.+)$', raw_pattern)
            if guard_match:
                raw_pattern = guard_match.group(1).strip()
                guard = guard_match.group(2).strip()

            if raw_pattern == "_":
                case_infos.append({"pattern": "_", "guard": guard, "or_values": None, "seq_pattern": None})
                continue

            seq_m = re.match(r'^\[([^\]]+)\]$', raw_pattern)
            if seq_m:
                inner = seq_m.group(1).strip()
                elements = [e.strip() for e in inner.split(",")]
                all_simple_vars = all(re.match(r'^[a-z_]\w*$', e) for e in elements)
                if all_simple_vars:
                    case_infos.append({"pattern": raw_pattern, "guard": guard, "or_values": None, "seq_pattern": elements})
                    continue

            or_parts = [p.strip() for p in raw_pattern.split("|")]
            if len(or_parts) > 1:
                all_simple = True
                for part in or_parts:
                    if not (re.match(r'^-?\d+$', part) or re.match(r'^"[^"]*"$', part) or
                            re.match(r"^'[^']*'$", part) or re.match(r'^[A-Z]\w*$', part) or
                            re.match(r'^[A-Z]\w*\.\w+$', part) or
                            (re.match(r'^\w+$', part) and part in ('True', 'False', 'None'))):
                        all_simple = False
                        break
                if all_simple:
                    case_infos.append({"pattern": raw_pattern, "guard": guard, "or_values": or_parts, "seq_pattern": None})
                    continue
                else:
                    can_convert = False
                    break

            if (re.match(r'^-?\d+$', raw_pattern) or re.match(r'^"[^"]*"$', raw_pattern) or
                    re.match(r"^'[^']*'$", raw_pattern) or re.match(r'^[A-Z]\w*$', raw_pattern) or
                    re.match(r'^[A-Z]\w*\.\w+$', raw_pattern) or
                    (re.match(r'^\w+$', raw_pattern) and raw_pattern in ('True', 'False', 'None'))):
                case_infos.append({"pattern": raw_pattern, "guard": guard, "or_values": None, "seq_pattern": None})
                continue

            if re.match(r'^[a-z]\w*\.[A-Z]\w*$', raw_pattern):
                case_infos.append({"pattern": raw_pattern, "guard": guard, "or_values": None, "seq_pattern": None})
                continue

            can_convert = False
            break

        if not can_convert:
            new_block = []
            for k in range(match_start, match_end + 1):
                if k < len(lines):
                    new_block.append(match_indent + "# " + lines[k].lstrip() if lines[k].strip() else lines[k])
            new_block.insert(0, f"{match_indent}# TODO: Python 3.8 compat - match/case block needs manual conversion")
            new_block.append(f"{match_indent}pass  # placeholder for removed match/case")
            lines[match_start:match_end + 1] = new_block
            continue

        new_block = []
        first_case = True

        for ci, (case_line_idx, case_info) in enumerate(zip(case_line_indices, case_infos)):
            case_line = lines[case_line_idx]
            case_m = re.match(r"^(\s+)case\s+(.+):$", case_line)
            case_indent = case_m.group(1)

            pattern = case_info["pattern"]
            guard = case_info["guard"]
            or_values = case_info["or_values"]
            seq_pattern = case_info.get("seq_pattern")

            condition = None
            destructure_lines = []
            if pattern == "_":
                condition = None
            elif seq_pattern:
                n = len(seq_pattern)
                condition = f"len({match_expr}) == {n}"
                if n == 1:
                    destructure_lines.append(f"{match_indent}    {seq_pattern[0]} = {match_expr}[0]")
                else:
                    indices = ", ".join(f"{match_expr}[{i}]" for i in range(n))
                    destructure_lines.append(f"{match_indent}    {', '.join(seq_pattern)} = {indices}")
            elif or_values:
                condition = f"{match_expr} in ({', '.join(or_values)})"
            else:
                condition = f"{match_expr} == {pattern}"

            if guard:
                if condition:
                    condition = f"{condition} and {guard}"
                else:
                    condition = guard

            if first_case:
                if condition is None:
                    new_block.append(f"{match_indent}else:")
                else:
                    new_block.append(f"{match_indent}if {condition}:")
                first_case = False
            else:
                if condition is None:
                    new_block.append(f"{match_indent}else:")
                else:
                    new_block.append(f"{match_indent}elif {condition}:")

            for dl in destructure_lines:
                new_block.append(dl)

            body_start = case_line_idx + 1
            if ci + 1 < len(case_line_indices):
                body_end = case_line_indices[ci + 1]
            else:
                body_end = match_end + 1

            indent_diff = len(case_indent) - len(match_indent)
            for k in range(body_start, body_end):
                if k < len(lines):
                    body_line = lines[k]
                    if body_line.strip() == "":
                        new_block.append(body_line)
                    elif body_line.startswith(case_indent):
                        new_block.append(body_line[indent_diff:])
                    else:
                        new_block.append(body_line)

        lines[match_start:match_end + 1] = new_block

    return "\n".join(lines)


def fix_typing_311_plus(content):
    modified = False

    if "NotRequired" in content and "from typing import" in content:
        m = re.search(r"^from typing import (.+)$", content, re.MULTILINE)
        if m and "NotRequired" in m.group(1):
            imports = [x.strip() for x in m.group(1).split(",")]
            if "NotRequired" in imports:
                imports.remove("NotRequired")
                imports_str = ", ".join(imports) if imports else ""
                if imports_str:
                    content = content.replace(m.group(0), f"from typing import {imports_str}")
                else:
                    content = content.replace(m.group(0) + "\n", "")
                content = re.sub(
                    r"^(from typing import .+\n)",
                    r"\1try:\n    from typing import NotRequired\nexcept ImportError:\n    from typing_extensions import NotRequired\n",
                    content,
                    count=1,
                )
                modified = True

    if "Required" in content and "from typing import" in content:
        m = re.search(r"^from typing import (.+)$", content, re.MULTILINE)
        if m and "Required" in m.group(1):
            imports = [x.strip() for x in m.group(1).split(",")]
            if "Required" in imports:
                imports.remove("Required")
                imports_str = ", ".join(imports) if imports else ""
                if imports_str:
                    content = content.replace(m.group(0), f"from typing import {imports_str}")
                else:
                    content = content.replace(m.group(0) + "\n", "")
                content = re.sub(
                    r"^(from typing import .+\n)",
                    r"\1try:\n    from typing import Required\nexcept ImportError:\n    from typing_extensions import Required\n",
                    content,
                    count=1,
                )
                modified = True

    if "from collections.abc import" in content and "Buffer" in content:
        m = re.search(r"^from collections\.abc import (.+)$", content, re.MULTILINE)
        if m and "Buffer" in m.group(1):
            imports = [x.strip() for x in m.group(1).split(",")]
            has_buffer = "Buffer" in imports
            if has_buffer:
                imports.remove("Buffer")
                imports_str = ", ".join(imports) if imports else ""
                if imports_str:
                    content = content.replace(m.group(0), f"from collections.abc import {imports_str}")
                else:
                    content = content.replace(m.group(0) + "\n", "")
                content = re.sub(
                    r"^(from collections\.abc import .+\n)",
                    r"\1try:\n    from collections.abc import Buffer\nexcept ImportError:\n    from typing import Buffer\n",
                    content,
                    count=1,
                )
                modified = True

    if "typing.assert_never" in content:
        content = content.replace(
            "typing.assert_never",
            "typing_extensions.assert_never if hasattr(typing, 'assert_never') else lambda x: None  # assert_never compat"
        )
        content = re.sub(
            r"^(import typing\n)",
            r"\1import typing_extensions\n",
            content,
        )
        modified = True

    return content


def fix_pep585_604(content):
    if "from __future__ import annotations" in content:
        return content

    pep585_types = {"list", "dict", "set", "frozenset", "tuple", "type"}
    needs_future = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for t in pep585_types:
            if re.search(rf"\b{t}\[", line):
                if ":" in line or "->" in line or "def " in line or ("=" in line and "==" not in line):
                    needs_future = True
                    break
        if needs_future:
            break

    if not needs_future:
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if re.search(r"\w+\s*\|\s*\w+", line):
                if ":" in line or "->" in line or "def " in line:
                    needs_future = True
                    break

    if needs_future:
        lines = content.split("\n")
        insert_pos = _find_future_import_position(lines)
        lines.insert(insert_pos, "from __future__ import annotations")
        content = "\n".join(lines)

    return content


def _find_future_import_position(lines):
    insert_pos = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if line.startswith("#!") or line.startswith("# -*-") or line.startswith("# vim:") or line.startswith("# coding:"):
            insert_pos = i + 1
            i += 1
            continue

        if stripped == "" or stripped.startswith("#"):
            i += 1
            continue

        if stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith('r"""') or stripped.startswith("r'''"):
            quote = '"""' if '"""' in stripped[:4] else "'''"
            if stripped.count(quote) >= 2 and stripped.endswith(quote) and len(stripped) > len(quote):
                insert_pos = i + 1
                break
            for j in range(i + 1, len(lines)):
                if quote in lines[j]:
                    insert_pos = j + 1
                    break
            else:
                insert_pos = len(lines)
            break

        insert_pos = i
        break

    return insert_pos


def fix_removeprefix_removesuffix(content):
    if ".removeprefix(" not in content and ".removesuffix(" not in content:
        return content

    _OBJ_PATTERN = r"((?:\w+\.)*\w+(?:\[[^\]]*\])*(?:\(\))*|\"[^\"]*\"|'[^']*'|b\"[^\"]*\"|b'[^']*'|B\"[^\"]*\"|B'[^']*')"

    def find_matching_paren(s, start):
        depth = 0
        for i in range(start, len(s)):
            if s[i] == '(':
                depth += 1
            elif s[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def find_obj_start(s, dot_pos):
        if dot_pos <= 0:
            return -1
        i = dot_pos - 1
        if s[i] == ')':
            depth = 1
            i -= 1
            while i >= 0 and depth > 0:
                if s[i] == ')':
                    depth += 1
                elif s[i] == '(':
                    depth -= 1
                i -= 1
            if depth != 0:
                return -1
            i += 1
            while i > 0 and (s[i-1].isalnum() or s[i-1] in '._'):
                i -= 1
            return i
        elif s[i] == '"' or s[i] == "'":
            quote_char = s[i]
            j = i - 1
            if j >= 0 and s[j] in 'bB':
                j -= 1
                if j >= 0 and s[j] in 'rR':
                    j -= 1
            i = j + 1
            return i
        elif s[i].isalnum() or s[i] == '_':
            while i > 0 and (s[i-1].isalnum() or s[i-1] in '._'):
                i -= 1
            return i
        return -1

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        while ".removeprefix(" in line or ".removesuffix(" in line:
            m_prefix = re.search(r"\.removeprefix\(", line)
            m_suffix = re.search(r"\.removesuffix\(", line)

            if m_prefix and m_suffix:
                if m_prefix.start() < m_suffix.start():
                    dot_pos = m_prefix.start()
                    is_prefix = True
                else:
                    dot_pos = m_suffix.start()
                    is_prefix = False
            elif m_prefix:
                dot_pos = m_prefix.start()
                is_prefix = True
            elif m_suffix:
                dot_pos = m_suffix.start()
                is_prefix = False
            else:
                break

            obj_start = find_obj_start(line, dot_pos)
            if obj_start == -1:
                break

            obj = line[obj_start:dot_pos]

            method_call_start = dot_pos
            arg_start = line.index("(", method_call_start) + 1
            arg_end = find_matching_paren(line, arg_start - 1)
            if arg_end == -1:
                break

            arg = line[arg_start:arg_end]

            if is_prefix:
                replacement = f"({obj}[len({arg}):] if {obj}.startswith({arg}) else {obj})"
            else:
                replacement = f"({obj}[:-len({arg})] if {arg} and {obj}.endswith({arg}) else {obj})"

            line = line[:obj_start] + replacement + line[arg_end + 1:]

        new_lines.append(line)

    return "\n".join(new_lines)


def fix_functools_cache(content):
    if "functools" not in content and "cache" not in content:
        return content

    content = re.sub(
        r"from functools import ([^\n]*\b)cache(\b[^\n]*)",
        r"from functools import \1lru_cache\2",
        content,
    )
    content = content.replace("from functools import cache", "from functools import lru_cache")
    content = re.sub(r"@functools\.cache\b(?!\()", "@functools.lru_cache(maxsize=None)", content)
    content = re.sub(r"@cache\b(?!\()", "@functools.lru_cache(maxsize=None)", content)

    return content


def fix_importlib_metadata_import(content):
    if "importlib.metadata" not in content and "importlib import metadata" not in content:
        return content

    if re.search(r"try:\s*\n\s*(?:import|from)\s+importlib[.\s]metadata", content):
        return content

    if re.search(r"try:\s*\n\s*from importlib import metadata", content):
        return content

    if re.search(r"importlib_metadata", content):
        return content

    content = re.sub(
        r"^(\s*)import importlib\.metadata as (\w+)\n",
        lambda m: f"{m.group(1)}try:\n{m.group(1)}    import importlib.metadata as {m.group(2)}\n{m.group(1)}except ImportError:\n{m.group(1)}    import importlib_metadata as {m.group(2)}\n",
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r"^(\s*)import importlib\.metadata\n",
        lambda m: f"{m.group(1)}try:\n{m.group(1)}    import importlib.metadata\n{m.group(1)}except ImportError:\n{m.group(1)}    import importlib_metadata\n{m.group(1)}    importlib.metadata = importlib_metadata\n",
        content,
        flags=re.MULTILINE,
    )

    lines = content.split("\n")
    new_lines = []
    collected_items = []
    collected_indent = None

    def flush_collected():
        if not collected_items:
            return
        indent = collected_indent
        new_lines.append(f"{indent}try:")
        for item in collected_items:
            new_lines.append(f"{indent}    from importlib.metadata import {item}")
        new_lines.append(f"{indent}except ImportError:")
        for item in collected_items:
            new_lines.append(f"{indent}    from importlib_metadata import {item}")

    for line in lines:
        m = re.match(r"^(\s*)from importlib\.metadata import (.+)$", line)
        if m:
            indent = m.group(1)
            items = [item.strip() for item in m.group(2).split(",")]
            if collected_indent is not None and collected_indent == indent:
                collected_items.extend(items)
            else:
                flush_collected()
                collected_items = items
                collected_indent = indent
        elif re.match(r"^(\s*)from importlib import metadata$", line):
            flush_collected()
            collected_items = []
            collected_indent = None
            indent_m = re.match(r"^(\s*)from importlib import metadata$", line)
            indent = indent_m.group(1)
            new_lines.append(f"{indent}try:")
            new_lines.append(f"{indent}    from importlib import metadata")
            new_lines.append(f"{indent}except ImportError:")
            new_lines.append(f"{indent}    import importlib_metadata")
            new_lines.append(f"{indent}    importlib.metadata = importlib_metadata")
        else:
            flush_collected()
            collected_items = []
            collected_indent = None
            new_lines.append(line)

    flush_collected()

    return "\n".join(new_lines)


def fix_typing_imports(content):
    if "from typing import" not in content:
        return content

    if "from typing_extensions import" in content:
        return content

    PY310_PLUS = {"ParamSpec", "Concatenate", "TypeGuard", "TypeAlias"}
    PY311_PLUS = {"Self", "LiteralString", "assert_never"}
    PY312_PLUS = {"TypeAliasType", "TypeVarTuple", "override"}

    ALL_NEW = PY310_PLUS | PY311_PLUS | PY312_PLUS

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        m = re.match(r"^from typing import (.+)$", line)
        if m:
            items = [item.strip() for item in m.group(1).split(",")]
            py38_items = []
            new_items = []
            for item in items:
                name = item.strip()
                base_name = name.split(" as ")[0].split("[")[0].split(".")[0].strip()
                if base_name in ALL_NEW:
                    new_items.append(name)
                else:
                    py38_items.append(item)

            if py38_items:
                new_lines.append("from typing import " + ", ".join(py38_items))
            if new_items:
                for item in new_items:
                    as_match = re.match(r"(\w+)\s+as\s+(\w+)", item)
                    if as_match:
                        orig_name = as_match.group(1)
                        alias_name = as_match.group(2)
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {orig_name} as {alias_name}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {orig_name} as {alias_name}")
                    else:
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {item}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {item}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def _find_matching_paren(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_union_types(types_str):
    parts = []
    depth = 0
    current = []
    for ch in types_str:
        if ch in '([':
            depth += 1
            current.append(ch)
        elif ch in ')]':
            depth -= 1
            current.append(ch)
        elif ch == '|' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current).strip())
    return [p for p in parts if p]


def _fix_isinstance_or_issubclass_union(content, func_name):
    if func_name not in content or "|" not in content:
        return content

    result = []
    i = 0
    while i < len(content):
        idx = content.find(f"{func_name}(", i)
        if idx == -1:
            result.append(content[i:])
            break

        if idx > 0 and (content[idx - 1].isalnum() or content[idx - 1] == '_'):
            result.append(content[i:idx + 1])
            i = idx + 1
            continue

        result.append(content[i:idx])

        paren_start = idx + len(func_name)
        paren_end = _find_matching_paren(content, paren_start)
        if paren_end == -1:
            result.append(content[idx:])
            break

        call_content = content[paren_start + 1:paren_end]

        comma_pos = _find_top_level_comma(call_content)
        if comma_pos == -1:
            result.append(content[idx:paren_end + 1])
            i = paren_end + 1
            continue

        obj = call_content[:comma_pos].strip()
        types_str = call_content[comma_pos + 1:].strip()

        if '|' not in types_str:
            result.append(content[idx:paren_end + 1])
            i = paren_end + 1
            continue

        if types_str.startswith('(') and types_str.endswith(')'):
            inner = types_str[1:-1].strip()
            if '|' in inner:
                types_list = _split_union_types(inner)
                if len(types_list) > 1:
                    result.append(f"{func_name}({obj}, ({', '.join(types_list)}))")
                    i = paren_end + 1
                    continue

        types_list = _split_union_types(types_str)
        if len(types_list) > 1:
            all_simple = all(
                re.match(r'^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$', t) for t in types_list
            )
            if all_simple:
                result.append(f"{func_name}({obj}, ({', '.join(types_list)}))")
                i = paren_end + 1
                continue

        result.append(content[idx:paren_end + 1])
        i = paren_end + 1

    return ''.join(result)


def fix_isinstance_union(content):
    content = _fix_isinstance_or_issubclass_union(content, "isinstance")
    content = _fix_isinstance_or_issubclass_union(content, "issubclass")
    return content


def _find_expr_end(content, start):
    depth_paren = 0
    depth_bracket = 0
    depth_brace = 0
    i = start
    while i < len(content):
        ch = content[i]
        if ch in '([{':
            if ch == '(':
                depth_paren += 1
            elif ch == '[':
                depth_bracket += 1
            else:
                depth_brace += 1
            i += 1
        elif ch in ')]}':
            if ch == ')':
                depth_paren -= 1
            elif ch == ']':
                depth_bracket -= 1
            else:
                depth_brace -= 1
            if depth_paren < 0 or depth_bracket < 0 or depth_brace < 0:
                return i
            i += 1
        elif ch in ('"', "'"):
            quote = ch
            i += 1
            while i < len(content):
                if content[i] == '\\':
                    i += 2
                    continue
                if content[i] == quote:
                    i += 1
                    break
                i += 1
        elif ch == '#':
            while i < len(content) and content[i] != '\n':
                i += 1
        elif depth_paren == 0 and depth_bracket == 0 and depth_brace == 0:
            if ch in (' ', '\t', '\n', ';', ',', '=', '!', '<', '>', '&', '^', '%', '+', '-', '*', '/', ':', '?'):
                if ch == '=' and i > start and content[i - 1] in ('!', '<', '>', '='):
                    i += 1
                    continue
                if ch == '>' and i > start and content[i - 1] == '-':
                    i += 1
                    continue
                return i
            i += 1
        else:
            i += 1
    return i


def fix_dict_merge_operator(content):
    if "|" not in content and "|=" not in content:
        return content

    lines = content.split("\n")
    new_lines = []
    any_fixed = False
    in_triple_quote = False
    triple_quote_char = None

    for line in lines:
        stripped = line.strip()

        if in_triple_quote:
            new_lines.append(line)
            if triple_quote_char in line:
                count = line.count(triple_quote_char)
                if line.strip().startswith(triple_quote_char):
                    count -= 1
                if count % 2 == 1:
                    in_triple_quote = False
                    triple_quote_char = None
            continue

        for q in ('"""', "'''"):
            if q in line:
                before = line.split(q)[0]
                if before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
                    count = line.count(q)
                    if count == 1:
                        in_triple_quote = True
                        triple_quote_char = q
                    new_lines.append(line)
                    break
        else:
            if stripped.startswith("#"):
                new_lines.append(line)
                continue

            if "|" not in line and "|=" not in line:
                new_lines.append(line)
                continue

            if re.search(r'\bdef\b|\bclass\b|\bimport\b|\bfrom\b', stripped):
                new_lines.append(line)
                continue

            new_line = line
            new_line, did_fix_inplace = _fix_dict_inplace_merge_line(new_line)
            new_line, did_fix_merge = _fix_dict_merge_line(new_line)

            if did_fix_inplace or did_fix_merge:
                any_fixed = True

            new_lines.append(new_line)
            continue

        continue

    return "\n".join(new_lines)


def _fix_dict_inplace_merge_line(line):
    if "|=" not in line:
        return line, False

    m = re.search(r'(\w[\w.]*)\s*\|=\s*', line)
    if not m:
        return line, False

    var_name = m.group(1)

    skip_names = {'self', 'cls', 'int', 'float', 'str', 'bool', 'list', 'dict',
                  'set', 'tuple', 'bytes', 'type', 'super', 'object', 'None',
                  'True', 'False', 'print', 'len', 'range', 'enumerate', 'zip',
                  'map', 'filter', 'isinstance', 'issubclass', 'hasattr',
                  'getattr', 'setattr', 'callable', 'sorted', 'reversed',
                  'property', 'staticmethod', 'classmethod', 'abstractmethod'}
    if var_name in skip_names:
        return line, False

    if _is_in_string(line, m.start()):
        return line, False

    rhs_start = m.end()
    rhs_end = _find_expr_end(line, rhs_start)
    rhs = line[rhs_start:rhs_end].strip()

    if not rhs:
        return line, False

    if not _looks_like_dict_literal(rhs) and not _looks_like_dict_variable(rhs.strip()):
        return line, False

    lhs_prefix = line[:m.start()]
    rhs_suffix = line[rhs_end:]

    return f"{lhs_prefix}{var_name}.update({rhs}){rhs_suffix}", True


def _is_in_string(line, pos):
    in_string = False
    is_raw = False
    string_char = None
    i = 0
    while i < pos:
        if not in_string:
            if i + 1 < len(line) and line[i] in ('r', 'b', 'f', 'u') and line[i + 1] in ('"', "'"):
                in_string = True
                is_raw = (line[i] == 'r')
                string_char = line[i + 1]
                i += 2
                continue
            if line[i] in ('"', "'"):
                in_string = True
                is_raw = False
                string_char = line[i]
                i += 1
                continue
        else:
            if line[i] == '\\' and not is_raw:
                i += 2
                continue
            if line[i] == string_char:
                in_string = False
                i += 1
                continue
        i += 1
    return in_string


def _is_type_annotation_context(line, pipe_pos):
    before = line[:pipe_pos]
    after = line[pipe_pos + 1:]

    colon_match = re.search(r':\s*[^#]*$', before)
    if colon_match:
        before_colon = before[:colon_match.start()]
        stripped_before = before_colon.strip()
        if re.search(r'\w\s*$', stripped_before):
            return True

    arrow_match = re.search(r'->\s*[^#]*$', before)
    if arrow_match:
        return True

    bracket_depth = 0
    for ch in before:
        if ch == '[':
            bracket_depth += 1
        elif ch == ']':
            bracket_depth -= 1
    if bracket_depth > 0:
        return True

    brace_depth = 0
    for ch in before:
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
    if brace_depth > 0:
        return True

    if re.search(r'\|\|', before[-2:] if len(before) >= 2 else ''):
        return True
    if re.search(r'^\s*\|\|', after):
        return True

    if re.search(r'r["\']', before[-3:] if len(before) >= 3 else ''):
        in_raw_string = False
        i = len(before) - 1
        while i >= 0:
            if before[i] in ('"', "'"):
                quote_char = before[i]
                j = i - 1
                while j >= 0 and before[j] in ('r', 'b', 'f', 'u'):
                    j -= 1
                prefix = before[j+1:i]
                if 'r' in prefix:
                    in_raw_string = True
                break
            i -= 1
        if in_raw_string:
            return True

    return False


def _fix_dict_merge_line(line):
    if "|" not in line:
        return line, False

    if re.search(r'isinstance\s*\(|issubclass\s*\(', line):
        return line, False

    if re.search(r'\|\|', line):
        return line, False

    result = []
    i = 0
    fixed = False
    in_string = False
    is_raw = False
    string_char = None
    while i < len(line):
        if in_string:
            if line[i] == '\\' and not is_raw:
                result.append(line[i:i + 2])
                i += 2
                continue
            if line[i] == string_char:
                in_string = False
                result.append(line[i])
                i += 1
                continue
            result.append(line[i])
            i += 1
            continue

        if i + 1 < len(line) and line[i] in ('r', 'b', 'f', 'u') and line[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (line[i] == 'r')
            string_char = line[i + 1]
            result.append(line[i:i + 2])
            i += 2
            continue

        if line[i] in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = line[i]
            result.append(line[i])
            i += 1
            continue

        if line[i] == '|':
            if i + 1 < len(line) and line[i + 1] == '=':
                result.append(line[i:i + 2])
                i += 2
                continue

            if i > 0 and line[i - 1] == '|':
                result.append(line[i])
                i += 1
                continue

            if _is_type_annotation_context(line, i):
                result.append(line[i])
                i += 1
                continue

            left_start = _find_expr_start_reverse(result)
            right_end = _find_expr_end_forward(line, i + 1)

            if left_start is not None and right_end is not None:
                left_expr = ''.join(result[left_start:]).strip()
                right_expr = line[i + 1:right_end].strip()

                if left_expr and right_expr:
                    if not _is_likely_dict_merge(left_expr, right_expr):
                        result.append(line[i])
                        i += 1
                        continue

                    replacement = f"{{**{left_expr}, **{right_expr}}}"
                    result[left_start:] = [replacement]
                    i = right_end
                    fixed = True
                    continue

            result.append(line[i])
            i += 1
        else:
            result.append(line[i])
            i += 1

    return ''.join(result), fixed


def _is_clearly_not_dict(expr):
    expr = expr.strip()
    if not expr:
        return True

    if re.match(r'^\d+(\.\d+)?$', expr):
        return True

    if re.match(r'^(True|False|None)$', expr):
        return True

    if re.match(r'^["\']', expr):
        return True

    if re.match(r'^b["\']', expr):
        return True

    if re.match(r'^[A-Z]\w*$', expr):
        return True

    if expr in ('int', 'float', 'str', 'bool', 'bytes', 'list', 'tuple',
                'set', 'frozenset', 'type', 'complex', 'range', 'memoryview',
                'bytearray', 'object', 'super', 'property', 'classmethod',
                'staticmethod', 'abstractmethod'):
        return True

    return False


def _is_likely_dict_merge(left_expr, right_expr):
    left = left_expr.strip()
    right = right_expr.strip()

    if _is_clearly_not_dict(left) or _is_clearly_not_dict(right):
        return False

    if _looks_like_set_literal(left) or _looks_like_set_literal(right):
        return False

    if _looks_like_dict_literal(left) or _looks_like_dict_literal(right):
        return True

    if _looks_like_dict_variable(left) and _looks_like_dict_variable(right):
        return True

    return False


def _looks_like_set_literal(expr):
    expr = expr.strip()
    if not expr.startswith('{') or not expr.endswith('}'):
        return False
    inner = expr[1:-1].strip()
    if ':' in inner:
        return False
    if not inner:
        return False
    return True


def _looks_like_dict_literal(expr):
    expr = expr.strip()
    if not expr.startswith('{') or not expr.endswith('}'):
        return False
    inner = expr[1:-1].strip()
    if ':' in inner:
        return True
    return False


def _looks_like_dict_variable(expr):
    expr = expr.strip()
    if re.match(r'^[a-z_]\w*$', expr):
        dict_hints = ('dict', 'map', 'config', 'option', 'param', 'env',
                      'data', 'info', 'meta', 'header', 'cache', 'result',
                      'context', 'state', 'props', 'attr', 'field', 'entry',
                      'record', 'item', 'setting', 'var', 'kwarg', 'kwargs',
                      'd1', 'd2', 'd', 'd1_', 'd2_', 'defaults', 'override',
                      'base', 'extra', 'update', 'merged', 'combined',
                      'new_dict', 'old_dict', 'src', 'dst', 'target', 'source')
        name_lower = expr.lower()
        for hint in dict_hints:
            if hint in name_lower:
                return True
    return False


def _find_expr_start_reverse(result_chars):
    i = len(result_chars) - 1
    while i >= 0 and result_chars[i] in (' ', '\t'):
        i -= 1
    if i < 0:
        return 0
    depth = 0
    last_nonspace = i
    while i >= 0:
        ch = result_chars[i]
        if ch in ')]}':
            depth += 1
        elif ch in '([{':
            depth -= 1
        elif depth == 0:
            if ch in (' ', '\t', ',', ';', '=', '!', '<', '>', '&', '^', '%', '+', '-', '*', '/', ':', '(', '[', '{'):
                if ch == '=' and i > 0 and result_chars[i - 1] in ('!', '<', '>', '='):
                    return i - 1
                if ch == '-' and i > 0 and result_chars[i - 1] == '>':
                    return i - 1
                return i + 1
        i -= 1
    return 0 if depth <= 0 else None


def _find_expr_end_forward(line, start):
    i = start
    while i < len(line) and line[i] in (' ', '\t'):
        i += 1
    if i >= len(line):
        return len(line)
    depth = 0
    while i < len(line):
        ch = line[i]
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            if depth == 0:
                return i
            depth -= 1
        elif depth == 0:
            if ch in (' ', '\t', ',', ';', '=', '!', '<', '>', '&', '^', '%', '+', '-', '*', '/', ':', ')', ']', '}'):
                if ch == '=' and i > start and line[i - 1] in ('!', '<', '>', '='):
                    i += 1
                    continue
                return i
        i += 1
    return len(line) if depth <= 0 else None


def fix_annotated_import(content):
    if "Annotated" not in content:
        return content

    if "from typing import" not in content and "from typing_extensions import" not in content:
        if "import typing" in content:
            content = re.sub(
                r"(import typing\n)",
                r"\1try:\n    from typing import Annotated\nexcept ImportError:\n    from typing_extensions import Annotated\n",
                content,
            )
        return content

    annotated_m = None
    for m in re.finditer(r"^from typing import (.+)$", content, re.MULTILINE):
        imports_str = m.group(1)
        imports = [x.strip() for x in imports_str.split(",")]
        if "Annotated" in imports:
            annotated_m = m
            break

    if not annotated_m:
        return content

    imports_str = annotated_m.group(1)
    imports = [x.strip() for x in imports_str.split(",")]
    imports.remove("Annotated")
    remaining = ", ".join(imports) if imports else ""

    if remaining:
        new_line = f"from typing import {remaining}"
    else:
        new_line = ""

    old_line = annotated_m.group(0)

    annotated_block = "try:\n    from typing import Annotated\nexcept ImportError:\n    from typing_extensions import Annotated"

    if remaining:
        content = content.replace(old_line, new_line + "\n" + annotated_block, 1)
    else:
        content = content.replace(old_line, annotated_block, 1)

    return content


def fix_math_lcm(content):
    if "math.lcm" not in content:
        return content

    if "def lcm(" in content or "def _lcm(" in content:
        return content

    lines = content.split("\n")
    new_lines = []
    needs_compat = False

    for line in lines:
        if "math.lcm" in line:
            needs_compat = True
            line = line.replace("math.lcm(", "_math_lcm_compat(")
        new_lines.append(line)

    if needs_compat:
        compat_code = (
            "try:\n"
            "    from math import lcm as _math_lcm_compat\n"
            "except ImportError:\n"
            "    from functools import reduce\n"
            "    from math import gcd\n"
            "    def _math_lcm_compat(*integers):\n"
            "        if not integers:\n"
            "            return 1\n"
            "        return reduce(lambda a, b: a * b // gcd(a, b), integers)\n"
        )

        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return "\n".join(new_lines)


def fix_math_nextafter_ulp(content):
    needs_nextafter = "math.nextafter" in content
    needs_ulp = "math.ulp" in content

    if not needs_nextafter and not needs_ulp:
        return content

    if needs_nextafter and ("def _math_nextafter_compat" in content or "nextafter" in content and "def nextafter" in content):
        needs_nextafter = False
    if needs_ulp and ("def _math_ulp_compat" in content or "def ulp" in content):
        needs_ulp = False

    if not needs_nextafter and not needs_ulp:
        return content

    lines = content.split("\n")
    new_lines = []
    needs_nextafter_compat = False
    needs_ulp_compat = False

    for line in lines:
        if needs_nextafter and "math.nextafter" in line:
            needs_nextafter_compat = True
            line = line.replace("math.nextafter(", "_math_nextafter_compat(")
        if needs_ulp and "math.ulp" in line:
            needs_ulp_compat = True
            line = line.replace("math.ulp(", "_math_ulp_compat(")
        new_lines.append(line)

    compat_parts = []
    if needs_nextafter_compat:
        compat_parts.append(
            "try:\n"
            "    from math import nextafter as _math_nextafter_compat\n"
            "except ImportError:\n"
            "    import struct\n"
            "    import math as _math_mod\n"
            "    def _math_nextafter_compat(x, y):\n"
            "        if x == y:\n"
            "            return y\n"
            "        if _math_mod.isnan(x) or _math_mod.isnan(y):\n"
            "            return float('nan')\n"
            "        if _math_mod.isinf(x):\n"
            "            return x\n"
            "        if x == 0.0:\n"
            "            return _math_copysign(_math_mod.ldexp(1.0, -1074), y)\n"
            "        bits = struct.unpack('=Q', struct.pack('=d', _math_copysign(x, 1.0)))[0]\n"
            "        if (x < y) == (x >= 0):\n"
            "            bits += 1\n"
            "        else:\n"
            "            bits -= 1\n"
            "        return _math_copysign(struct.unpack('=d', struct.pack('=Q', bits))[0], x)\n"
        )
    if needs_ulp_compat:
        compat_parts.append(
            "try:\n"
            "    from math import ulp as _math_ulp_compat\n"
            "except ImportError:\n"
            "    import math as _math_mod\n"
            "    def _math_ulp_compat(x):\n"
            "        if _math_mod.isnan(x):\n"
            "            return x\n"
            "        if _math_mod.isinf(x):\n"
            "            return abs(x)\n"
            "        x_abs = abs(x)\n"
            "        if x_abs < _math_mod.ldexp(1.0, -1022):\n"
            "            return _math_mod.ldexp(1.0, -1074)\n"
            "        _man, _exp = _math_mod.frexp(x_abs)\n"
            "        return _math_mod.ldexp(1.0, _exp - 53)\n"
        )

    if needs_nextafter_compat:
        compat_parts.insert(0 if needs_nextafter_compat else len(compat_parts),
            "def _math_copysign(x, y):\n"
            "    import math as _m\n"
            "    return _m.copysign(x, y)\n"
        )

    if compat_parts:
        insert_pos = _find_compat_insert_position(new_lines)
        compat_code = "\n".join(compat_parts)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return "\n".join(new_lines)


def fix_collections_abc_aliases(content):
    if "collections" not in content:
        return content

    abc_names = [
        "Mapping", "MutableMapping", "Iterable", "Iterator",
        "Sequence", "MutableSequence", "Set", "MutableSet",
        "Callable", "Container", "Hashable", "Sized",
        "Collection", "Reversible", "Coroutine", "AsyncIterable",
        "AsyncIterator", "AsyncGenerator", "Generator",
        "ByteString", "MutableMapping",
    ]

    needs_fix = False
    for name in abc_names:
        pattern = rf"from collections import .*{name}"
        if re.search(pattern, content):
            needs_fix = True
            break

    if not needs_fix:
        for name in abc_names:
            if re.search(rf"\bcollections\.{name}\b", content):
                needs_fix = True
                break

    if not needs_fix:
        return content

    lines = content.split("\n")
    new_lines = []

    for line in lines:
        m = re.match(r"^from collections import (.+)$", line)
        if m:
            imports = [x.strip() for x in m.group(1).split(",")]
            abc_imports = []
            other_imports = []

            for imp in imports:
                base = imp.split(" as ")[0].split("[")[0].strip()
                if base in abc_names:
                    abc_imports.append(imp)
                else:
                    other_imports.append(imp)

            if abc_imports:
                if other_imports:
                    new_lines.append(f"from collections import {', '.join(other_imports)}")
                new_lines.append(f"from collections.abc import {', '.join(abc_imports)}")
            else:
                new_lines.append(line)
        else:
            for name in abc_names:
                line = re.sub(
                    rf"\bcollections\.{name}\b",
                    f"collections.abc.{name}",
                    line,
                )
            new_lines.append(line)

    return "\n".join(new_lines)


def fix_random_randbytes(content):
    if "random.randbytes" not in content and ".randbytes(" not in content:
        return content

    if "def randbytes(" in content or "def _randbytes_compat" in content:
        return content

    lines = content.split("\n")
    new_lines = []
    needs_compat = False

    for line in lines:
        if "random.randbytes(" in line:
            needs_compat = True
            line = line.replace("random.randbytes(", "random._randbytes_compat(")
        elif ".randbytes(" in line and "random" in line:
            needs_compat = True
            line = re.sub(r'(\w+)\.randbytes\(', r'\1._randbytes_compat(', line)
        new_lines.append(line)

    if needs_compat:
        compat_code = (
            "try:\n"
            "    from random import randbytes as _randbytes_compat_orig\n"
            "    import random as _random_mod\n"
            "    _random_mod._randbytes_compat = staticmethod(_randbytes_compat_orig)\n"
            "except ImportError:\n"
            "    import random as _random_mod\n"
            "    def _randbytes_compat(n):\n"
            "        return _random_mod.getrandbits(n * 8).to_bytes(n, 'little')\n"
            "    _random_mod._randbytes_compat = staticmethod(_randbytes_compat)\n"
        )

        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return "\n".join(new_lines)


def fix_ast_unparse(content):
    if "ast.unparse" not in content:
        return content

    if "def unparse(" in content or "def _ast_unparse_compat" in content:
        return content

    lines = content.split("\n")
    new_lines = []
    needs_compat = False

    for line in lines:
        if "ast.unparse(" in line:
            needs_compat = True
            line = line.replace("ast.unparse(", "_ast_unparse_compat(")
        new_lines.append(line)

    if needs_compat:
        compat_code = (
            "try:\n"
            "    from ast import unparse as _ast_unparse_compat\n"
            "except ImportError:\n"
            "    import ast as _ast_mod\n"
            "    def _ast_unparse_compat(node):\n"
            "        try:\n"
            "            import astunparse\n"
            "            return astunparse.unparse(node)\n"
            "        except ImportError:\n"
            "            return _ast_mod.dump(node)\n"
        )

        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return "\n".join(new_lines)


def fix_bytes_removeprefix_removesuffix(content):
    return fix_removeprefix_removesuffix(content)


def _find_matching_paren_simple(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_compat_insert_position(lines):
    insert_pos = 0
    in_docstring = False
    docstring_quote = None
    paren_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if i == 0 and stripped.startswith("#!"):
            insert_pos = i + 1
            continue

        if stripped.startswith("# -*-") or stripped.startswith("# vim:") or stripped.startswith("# coding:"):
            insert_pos = i + 1
            continue

        if paren_depth > 0:
            for ch in stripped:
                if ch in '([{':
                    paren_depth += 1
                elif ch in ')]}':
                    paren_depth -= 1
            if paren_depth <= 0:
                paren_depth = 0
                insert_pos = i + 1
            continue

        if stripped == "" or stripped.startswith("#"):
            insert_pos = i + 1
            continue

        if not in_docstring:
            for q in ('"""', "'''"):
                if stripped.startswith(q):
                    docstring_quote = q
                    if stripped.count(q) >= 2 and stripped.endswith(q) and len(stripped) > len(q):
                        insert_pos = i + 1
                        in_docstring = False
                    else:
                        in_docstring = True
                    break
            if in_docstring:
                continue
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue

        if in_docstring:
            if docstring_quote and docstring_quote in stripped:
                insert_pos = i + 1
                in_docstring = False
            continue

        if stripped.startswith("from __future__"):
            for ch in stripped:
                if ch in '([{':
                    paren_depth += 1
                elif ch in ')]}':
                    paren_depth -= 1
            if paren_depth <= 0:
                paren_depth = 0
                insert_pos = i + 1
            else:
                insert_pos = i + 1
            continue

        if stripped.startswith("import ") or stripped.startswith("from "):
            for ch in stripped:
                if ch in '([{':
                    paren_depth += 1
                elif ch in ')]}':
                    paren_depth -= 1
            if paren_depth <= 0:
                paren_depth = 0
                insert_pos = i + 1
            else:
                insert_pos = i + 1
            continue

        break

    return insert_pos


def _find_top_level_comma(s):
    depth = 0
    for i, ch in enumerate(s):
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        elif ch == ',' and depth == 0:
            return i
    return -1


def fix_zoneinfo(content):
    if "import zoneinfo" not in content and "from zoneinfo" not in content:
        return content

    if re.search(r"try:\s*\n\s*import zoneinfo", content):
        return content

    content = content.replace(
        "import zoneinfo\n",
        "try:\n    import zoneinfo\nexcept ImportError:\n    from backports import zoneinfo\n"
    )

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        m = re.match(r"^from zoneinfo import (.+)$", line)
        if m:
            items = [item.strip() for item in m.group(1).split(",")]
            for item in items:
                new_lines.append("try:")
                new_lines.append(f"    from zoneinfo import {item}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    from backports.zoneinfo import {item}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def fix_graphlib(content):
    if "import graphlib" not in content and "from graphlib" not in content:
        return content

    if re.search(r"try:\s*\n\s*import graphlib", content):
        return content

    content = content.replace(
        "import graphlib\n",
        "try:\n    import graphlib\nexcept ImportError:\n    import graphlib_backport as graphlib\n"
    )

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        m = re.match(r"^from graphlib import (.+)$", line)
        if m:
            items = [item.strip() for item in m.group(1).split(",")]
            for item in items:
                new_lines.append("try:")
                new_lines.append(f"    from graphlib import {item}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    from graphlib_backport import {item}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def fix_zip_strict(content):
    if "strict=" not in content:
        return content
    if not re.search(r'\bzip\s*\(', content):
        return content

    needs_compat = False

    def _replace_zip(m):
        nonlocal needs_compat
        prefix = m.group(1)
        inner = m.group(2)
        inner_stripped = inner.rstrip()
        if inner_stripped.endswith(','):
            inner_stripped = inner_stripped[:-1].rstrip()
        strict_m = re.search(r',?\s*strict\s*=\s*(True|False)\s*$', inner_stripped)
        if not strict_m:
            return m.group(0)
        strict_val = strict_m.group(1)
        args_only = inner_stripped[:strict_m.start()].rstrip()
        if args_only.endswith(','):
            args_only = args_only[:-1].rstrip()
        if strict_val == 'False':
            if args_only:
                needs_compat = False
                return f"{prefix}zip({args_only})"
            return m.group(0)
        else:
            needs_compat = True
            return f"{prefix}_zip_strict({args_only})"

    content = re.sub(
        r'(\b)zip\s*\(([^)]+)\)',
        _replace_zip,
        content,
    )

    if needs_compat and '_zip_strict' not in content:
        compat_code = """
def _zip_strict(*iterables):
    iterators = [iter(it) for it in iterables]
    while True:
        items = []
        for it in iterators:
            try:
                items.append(next(it))
            except StopIteration:
                if items:
                    raise ValueError("zip() argument with different length")
                return
        yield tuple(items)

"""
        new_lines = content.split('\n')
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())
        content = '\n'.join(new_lines)

    return content


def fix_int_bit_count(content):
    if ".bit_count()" not in content:
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith('"') or stripped.startswith("'"):
            new_lines.append(line)
            continue
        if '.bit_count()' in line and '_int_bit_count' not in line:
            new_line = re.sub(r'(?<!\w)([a-zA-Z_]\w*)\.bit_count\(\)', r'_int_bit_count(\1)', line)
            if new_line != line:
                needs_compat = True
                line = new_line
        new_lines.append(line)

    if needs_compat and '_int_bit_count' not in content:
        compat_code = (
            "def _int_bit_count(n):\n"
            "    return bin(n).count('1')\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_aiter_anext(content):
    has_aiter = bool(re.search(r'\baiter\s*\(', content))
    has_anext = bool(re.search(r'\banext\s*\(', content))
    if not has_aiter and not has_anext:
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if has_aiter and re.search(r'\baiter\s*\(', line) and '_aiter_compat' not in line:
            line = re.sub(r'\baiter\s*\(', '_aiter_compat(', line)
            needs_compat = True
        if has_anext and re.search(r'\banext\s*\(', line) and '_anext_compat' not in line:
            line = re.sub(r'\banext\s*\(', '_anext_compat(', line)
            needs_compat = True
        new_lines.append(line)

    if needs_compat:
        compat_parts = []
        if has_aiter and '_aiter_compat' not in content:
            compat_parts.append("def _aiter_compat(async_iterable):\n    return async_iterable.__aiter__()\n")
        if has_anext and '_anext_compat' not in content:
            compat_parts.append("def _anext_compat(async_iterator, default=_sentinel):\n    if default is _sentinel:\n        return async_iterator.__anext__()\n    else:\n        try:\n            return async_iterator.__anext__()\n        except StopAsyncIteration:\n            return default\n")
        if compat_parts:
            full_compat = ""
            if has_anext and '_sentinel' not in content:
                full_compat += "_sentinel = object()\n\n"
            full_compat += '\n'.join(compat_parts)
            insert_pos = _find_compat_insert_position(new_lines)
            new_lines.insert(insert_pos, full_compat.rstrip())

    return '\n'.join(new_lines)


def fix_bisect_key(content):
    if "bisect" not in content:
        return content
    if not re.search(r'\bbisect\w*\s*\([^)]*key\s*=', content):
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        m = re.search(r'\b(bisect(?:_left|_right|_insort|_insort_left|_insort_right)?)\s*\(([^)]*key\s*=\s*[^)]+)\)', line)
        if m:
            func_name = m.group(1)
            args_str = m.group(2)
            key_m = re.search(r',?\s*key\s*=\s*(lambda\s+[^,)]+)', args_str)
            if not key_m:
                key_m = re.search(r',?\s*key\s*=\s*(\w+)', args_str)
            if key_m:
                key_func = key_m.group(1)
                args_without_key = args_str[:key_m.start()].rstrip()
                if args_without_key.endswith(','):
                    args_without_key = args_without_key[:-1].rstrip()
                if 'insort' in func_name:
                    compat_func = f"_{func_name}_key_compat"
                else:
                    compat_func = f"_{func_name}_key_compat"
                replacement = f"{compat_func}({args_without_key}, {key_func})"
                line = line[:m.start()] + replacement + line[m.end():]
                needs_compat = True
        new_lines.append(line)

    content = '\n'.join(new_lines)

    if needs_compat:
        compat_code = """
import bisect as _bisect_mod

def _bisect_left_key_compat(a, x, key, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    x_key = key(x)
    while lo < hi:
        mid = (lo + hi) // 2
        if key(a[mid]) < x_key:
            lo = mid + 1
        else:
            hi = mid
    return lo

def _bisect_right_key_compat(a, x, key, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    x_key = key(x)
    while lo < hi:
        mid = (lo + hi) // 2
        if x_key < key(a[mid]):
            hi = mid
        else:
            lo = mid + 1
    return lo

def _bisect_insort_left_key_compat(a, x, key, lo=0, hi=None):
    i = _bisect_left_key_compat(a, x, key, lo, hi)
    a.insert(i, x)

def _bisect_insort_right_key_compat(a, x, key, lo=0, hi=None):
    i = _bisect_right_key_compat(a, x, key, lo, hi)
    a.insert(i, x)

"""
        if '_bisect_left_key_compat' not in content:
            new_lines = content.split('\n')
            insert_pos = _find_compat_insert_position(new_lines)
            new_lines.insert(insert_pos, compat_code.rstrip())
            content = '\n'.join(new_lines)

    return content


def fix_dataclass_slots(content):
    if "slots=" not in content:
        return content
    if not re.search(r'@(?:dataclasses\.)?dataclass\([^)]*slots\s*=', content):
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        m = re.match(r'^(\s*@(?:dataclasses\.)?dataclass\()(.+)(\)\s*)$', line)
        if m and 'slots=' in line:
            prefix = m.group(1)
            args_str = m.group(2)
            suffix = m.group(3)
            args_str = re.sub(r',?\s*slots\s*=\s*(True|False)', '', args_str)
            args_str = re.sub(r'^\s*,\s*', '', args_str)
            args_str = re.sub(r',\s*,', ',', args_str)
            args_str = args_str.strip()
            if args_str.endswith(','):
                args_str = args_str[:-1].strip()
            if args_str:
                new_lines.append(f"{prefix}{args_str}{suffix}")
            else:
                new_lines.append(f"{prefix.rstrip('(')}{suffix.lstrip(')')}")
        else:
            new_lines.append(line)

    content = '\n'.join(new_lines)
    content = content.replace('@dataclass()', '@dataclass')
    content = content.replace('@dataclasses.dataclass()', '@dataclasses.dataclass')

    return content


def fix_math_exp2_cbrt(content):
    needs_exp2 = "math.exp2" in content
    needs_cbrt = "math.cbrt" in content
    if not needs_exp2 and not needs_cbrt:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if needs_exp2 and 'math.exp2(' in line and '_math_exp2_compat' not in line:
            line = line.replace('math.exp2(', '_math_exp2_compat(')
        if needs_cbrt and 'math.cbrt(' in line and '_math_cbrt_compat' not in line:
            line = line.replace('math.cbrt(', '_math_cbrt_compat(')
        new_lines.append(line)

    compat_parts = []
    if needs_exp2 and '_math_exp2_compat' not in content:
        compat_parts.append(
            "def _math_exp2_compat(x):\n"
            "    try:\n"
            "        from math import exp2 as _math_exp2_compat\n"
            "        return _math_exp2_compat(x)\n"
            "    except ImportError:\n"
            "        return 2.0 ** x\n"
        )
    if needs_cbrt and '_math_cbrt_compat' not in content:
        compat_parts.append(
            "def _math_cbrt_compat(x):\n"
            "    try:\n"
            "        from math import cbrt as _math_cbrt_compat\n"
            "        return _math_cbrt_compat(x)\n"
            "    except ImportError:\n"
            "        return x ** (1.0 / 3.0) if x >= 0 else -((-x) ** (1.0 / 3.0))\n"
        )
    if compat_parts:
        full_compat = '\n'.join(compat_parts)
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, full_compat.rstrip())

    return '\n'.join(new_lines)


def fix_datetime_utc(content):
    if "datetime.UTC" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'datetime.UTC' in line and '_datetime_utc_compat' not in line:
            line = line.replace('datetime.UTC', '_datetime_utc_compat')
        new_lines.append(line)

    if '_datetime_utc_compat' not in content:
        compat_code = (
            "try:\n"
            "    from datetime import UTC as _datetime_utc_compat\n"
            "except ImportError:\n"
            "    from datetime import timezone\n"
            "    _datetime_utc_compat = timezone.utc\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_enum_strenum(content):
    if "StrEnum" not in content:
        return content
    if "from enum import" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        m = re.match(r'^from enum import (.+)$', line)
        if m and 'StrEnum' in m.group(1):
            items = [x.strip() for x in m.group(1).split(',')]
            has_strenum = 'StrEnum' in items
            if has_strenum:
                items.remove('StrEnum')
                if items:
                    new_lines.append("from enum import " + ", ".join(items))
                new_lines.append("try:")
                new_lines.append("    from enum import StrEnum")
                new_lines.append("except ImportError:")
                new_lines.append("    class StrEnum(str, enum.Enum):")
                new_lines.append("        def _generate_next_value_(name, start, count, last_values):")
                new_lines.append("            return name.lower()")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_contextlib_chdir(content):
    if "contextlib.chdir" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'contextlib.chdir(' in line and '_contextlib_chdir_compat' not in line:
            line = line.replace('contextlib.chdir(', '_contextlib_chdir_compat(')
        new_lines.append(line)

    if '_contextlib_chdir_compat' not in content:
        compat_code = (
            "try:\n"
            "    from contextlib import chdir as _contextlib_chdir_compat\n"
            "except ImportError:\n"
            "    import os\n"
            "    from contextlib import contextmanager\n"
            "    @contextmanager\n"
            "    def _contextlib_chdir_compat(path):\n"
            "        old_cwd = os.getcwd()\n"
            "        try:\n"
            "            os.chdir(path)\n"
            "            yield\n"
            "        finally:\n"
            "            os.chdir(old_cwd)\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_operator_call(content):
    if "operator.call" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'operator.call(' in line and '_operator_call_compat' not in line:
            line = line.replace('operator.call(', '_operator_call_compat(')
        new_lines.append(line)

    if '_operator_call_compat' not in content:
        compat_code = (
            "try:\n"
            "    from operator import call as _operator_call_compat\n"
            "except ImportError:\n"
            "    def _operator_call_compat(obj, /, *args, **kwargs):\n"
            "        return obj(*args, **kwargs)\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_hashlib_file_digest(content):
    if "hashlib.file_digest" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'hashlib.file_digest(' in line and '_hashlib_file_digest_compat' not in line:
            line = line.replace('hashlib.file_digest(', '_hashlib_file_digest_compat(')
        new_lines.append(line)

    if '_hashlib_file_digest_compat' not in content:
        compat_code = (
            "try:\n"
            "    from hashlib import file_digest as _hashlib_file_digest_compat\n"
            "except ImportError:\n"
            "    def _hashlib_file_digest(file, digest, /):\n"
            "        import hashlib\n"
            "        if isinstance(digest, str):\n"
            "            digest = hashlib.new(digest)\n"
            "        while True:\n"
            "            chunk = file.read(1 << 16)\n"
            "            if not chunk:\n"
            "                break\n"
            "            digest.update(chunk)\n"
            "        return digest\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_itertools_batched(content):
    if "itertools.batched" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'itertools.batched(' in line and '_itertools_batched_compat' not in line:
            line = line.replace('itertools.batched(', '_itertools_batched_compat(')
        new_lines.append(line)

    if '_itertools_batched_compat' not in content:
        compat_code = (
            "try:\n"
            "    from itertools import batched as _itertools_batched_compat\n"
            "except ImportError:\n"
            "    from itertools import islice\n"
            "    def _itertools_batched_compat(iterable, n, *, strict=False):\n"
            "        if n < 1:\n"
            "            raise ValueError('n must be at least one')\n"
            "        it = iter(iterable)\n"
            "        while True:\n"
            "            batch = tuple(islice(it, n))\n"
            "            if not batch:\n"
            "                break\n"
            "            if strict and len(batch) < n:\n"
            "                raise ValueError('batched(): incomplete batch')\n"
            "            yield batch\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_pathlib_walk(content):
    if "Path.walk" not in content:
        return content
    if "pathlib" not in content:
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if re.search(r'\bPath\.walk\(', line) and '_pathlib_walk_compat' not in line:
            line = re.sub(r'\bPath\.walk\(', '_pathlib_walk_compat(', line)
            needs_compat = True
        new_lines.append(line)

    if needs_compat and '_pathlib_walk_compat' not in content:
        compat_code = (
            "def _pathlib_walk_compat(path, top_down=True, on_error=None, follow_symlinks=False):\n"
            "    import os\n"
            "    from pathlib import Path as _Path\n"
            "    if hasattr(_Path, 'walk'):\n"
            "        for root, dirs, files in _Path.walk(path, top_down=top_down, on_error=on_error, follow_symlinks=follow_symlinks):\n"
            "            yield root, dirs, files\n"
            "        return\n"
            "    dirs = []\n"
            "    nondirs = []\n"
            "    walk_dir = str(path)\n"
            "    try:\n"
            "        scandir_it = os.scandir(walk_dir)\n"
            "    except OSError as e:\n"
            "        if on_error is not None:\n"
            "            on_error(e)\n"
            "        return\n"
            "    with scandir_it:\n"
            "        while True:\n"
            "            try:\n"
            "                entry = next(scandir_it)\n"
            "            except StopIteration:\n"
            "                break\n"
            "            try:\n"
            "                is_dir = entry.is_dir()\n"
            "            except OSError:\n"
            "                is_dir = False\n"
            "            if is_dir:\n"
            "                dirs.append(entry.name)\n"
            "            else:\n"
            "                nondirs.append(entry.name)\n"
            "    if top_down:\n"
            "        yield walk_dir, dirs, nondirs\n"
            "    for dirname in dirs:\n"
            "        new_path = os.path.join(walk_dir, dirname)\n"
            "        if follow_symlinks:\n"
            "            pass\n"
            "        else:\n"
            "            if os.path.islink(new_path):\n"
            "                continue\n"
            "        yield from _pathlib_walk_compat(new_path, top_down=top_down, on_error=on_error, follow_symlinks=follow_symlinks)\n"
            "    if not top_down:\n"
            "        yield walk_dir, dirs, nondirs\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def _strip_inline_comment(line):
    in_string = False
    quote_char = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == '\\' and i + 1 < len(line):
                i += 2
                continue
            if ch == quote_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
            elif ch == '#':
                return line[:i].rstrip()
        i += 1
    return line


def _join_continuation_lines(lines, start_idx):
    i = start_idx
    full_line = _strip_inline_comment(lines[i])
    orig_indent = re.match(r'^(\s*)', lines[i]).group(1)

    while i + 1 < len(lines):
        stripped = full_line.rstrip()
        if stripped.endswith('\\'):
            i += 1
            full_line = stripped[:-1] + ' ' + _strip_inline_comment(lines[i]).strip()
        elif stripped.endswith('(') or _count_unbalanced(full_line, '(', ')') > 0:
            i += 1
            full_line = full_line + ' ' + _strip_inline_comment(lines[i]).strip()
        else:
            break

    return full_line, i


def _count_unbalanced(s, open_ch, close_ch):
    depth = 0
    for ch in s:
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
    return depth


def _clean_import_names(names_str):
    names = names_str.strip()
    if names.startswith('(') and names.endswith(')'):
        names = names[1:-1].strip()
    elif names.startswith('('):
        names = names[1:].strip()
    names = names.rstrip(',').strip()
    names = re.sub(r'\s+', ' ', names)
    return names


def fix_distutils_import(content):
    if "distutils" not in content:
        return content

    if re.search(r"from setuptools import", content) and "distutils" not in content.split("from setuptools")[0]:
        return content

    if re.search(r"setuptools\._distutils", content):
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('#'):
            new_lines.append(line)
            i += 1
            continue

        full_line, end_idx = _join_continuation_lines(lines, i)

        m = re.match(r'^(\s*)from distutils\.(\w+) import (.+)$', full_line)
        if m and 'setuptools' not in full_line:
            indent = re.match(r'^(\s*)', line).group(1)
            submodule = m.group(2)
            names = _clean_import_names(m.group(3))
            needs_compat = True
            new_lines.append(f"{indent}try:")
            new_lines.append(f"{indent}    from distutils.{submodule} import {names}")
            new_lines.append(f"{indent}except ImportError:")
            new_lines.append(f"{indent}    from setuptools._distutils.{submodule} import {names}")
            i = end_idx + 1
            continue
        m = re.match(r'^(\s*)from distutils import (.+)$', full_line)
        if m and 'setuptools' not in full_line:
            indent = re.match(r'^(\s*)', line).group(1)
            names = _clean_import_names(m.group(2))
            needs_compat = True
            new_lines.append(f"{indent}try:")
            new_lines.append(f"{indent}    from distutils import {names}")
            new_lines.append(f"{indent}except ImportError:")
            new_lines.append(f"{indent}    from setuptools._distutils import {names}")
            i = end_idx + 1
            continue
        m = re.match(r'^(\s*)import distutils(\.\w+)?$', full_line)
        if m and 'setuptools' not in full_line:
            indent = re.match(r'^(\s*)', line).group(1)
            mod = full_line.strip()
            needs_compat = True
            new_lines.append(f"{indent}try:")
            new_lines.append(f"{indent}    {mod}")
            new_lines.append(f"{indent}except ImportError:")
            new_lines.append(f"{indent}    import setuptools._distutils as distutils")
            i = end_idx + 1
            continue
        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines)


def fix_compression_zstd(content):
    if "compression.zstd" not in content and "compression.lzma" not in content and "compression.bz2" not in content:
        return content
    if "from compression" not in content and "import compression" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'from compression import zstd' in line and '_compression_zstd_compat' not in line:
            new_lines.append("try:")
            new_lines.append("    from compression import zstd")
            new_lines.append("except ImportError:")
            new_lines.append("    import zstandard as zstd  # py38 compat")
        elif 'from compression import lzma' in line:
            new_lines.append("try:")
            new_lines.append("    from compression import lzma")
            new_lines.append("except ImportError:")
            new_lines.append("    import lzma  # py38 compat")
        elif 'from compression import bz2' in line:
            new_lines.append("try:")
            new_lines.append("    from compression import bz2")
            new_lines.append("except ImportError:")
            new_lines.append("    import bz2  # py38 compat")
        elif 'from compression import gzip' in line:
            new_lines.append("try:")
            new_lines.append("    from compression import gzip")
            new_lines.append("except ImportError:")
            new_lines.append("    import gzip  # py38 compat")
        elif 'from compression import zlib' in line:
            new_lines.append("try:")
            new_lines.append("    from compression import zlib")
            new_lines.append("except ImportError:")
            new_lines.append("    import zlib  # py38 compat")
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_concurrent_interpreters(content):
    if "concurrent.interpreters" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'from concurrent.interpreters import' in line:
            m = re.match(r'^from concurrent\.interpreters import (.+)$', line)
            if m:
                names = m.group(1)
                new_lines.append("try:")
                new_lines.append(f"    from concurrent.interpreters import {names}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    from interpreters import {names}  # py38 compat")
            else:
                new_lines.append(line)
        elif 'import concurrent.interpreters' in line:
            new_lines.append("try:")
            new_lines.append("    import concurrent.interpreters")
            new_lines.append("except ImportError:")
            new_lines.append("    import interpreters  # py38 compat")
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_annotationlib(content):
    if "annotationlib" not in content:
        return content

    if re.search(r'if\s+sys\.version_info\s*>=\s*\(\s*3\s*,\s*14\s*\)', content):
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'import annotationlib' in line or 'from annotationlib import' in line:
            indent = re.match(r'^(\s*)', line).group(1)
            new_lines.append(f"{indent}try:")
            new_lines.append(f"{indent}    {line.lstrip()}")
            new_lines.append(f"{indent}except ImportError:")
            new_lines.append(f"{indent}    pass  # annotationlib not available before Python 3.14")
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_frozendict(content):
    if "frozendict" not in content:
        return content
    if re.search(r'\bfrozendict\b', content) is None:
        return content

    lines = content.split('\n')
    new_lines = []
    has_frozendict_import = False
    for line in lines:
        if re.search(r'\bfrozendict\b', line) and 'import' not in line and '_frozendict_compat' not in line:
            line = re.sub(r'\bfrozendict\b', '_frozendict_compat', line)
        new_lines.append(line)
        if 'import frozendict' in line or 'from builtins import frozendict' in line:
            has_frozendict_import = True

    if not has_frozendict_import and '_frozendict_compat' in '\n'.join(new_lines):
        compat_code = (
            "try:\n"
            "    from builtins import frozendict as _frozendict_compat\n"
            "except ImportError:\n"
            "    from typing import Mapping as _frozendict_compat  # py38 compat fallback\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_sentinel(content):
    if "sentinel" not in content:
        return content
    if re.search(r'\bsentinel\s*\(', content) is None:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if re.search(r'\bsentinel\s*\(', line) and '_sentinel_compat' not in line:
            line = re.sub(r'\bsentinel\s*\(', '_sentinel_compat(', line)
        new_lines.append(line)

    if '_sentinel_compat' not in content:
        compat_code = (
            "try:\n"
            "    from builtins import sentinel as _sentinel_compat\n"
            "except ImportError:\n"
            "    def _sentinel_compat(name, *, repr=None):\n"
            "        class _Sentinel:\n"
            "            def __init__(self, name, repr_val=None):\n"
            "                self._name = name\n"
            "                self._repr = repr_val\n"
            "            def __repr__(self):\n"
            "                return self._repr if self._repr is not None else self._name\n"
            "            def __reduce__(self):\n"
            "                return (self.__class__, (self._name, self._repr))\n"
            "        return _Sentinel(name, repr)\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_profiling_module(content):
    if "profiling.tracing" not in content and "profiling.sampling" not in content:
        return content
    if "from profiling" not in content and "import profiling" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'from profiling.tracing import' in line:
            m = re.match(r'^from profiling\.tracing import (.+)$', line)
            if m:
                names = m.group(1)
                new_lines.append("try:")
                new_lines.append(f"    from profiling.tracing import {names}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    from cProfile import {names}  # py38 compat")
            else:
                new_lines.append(line)
        elif 'from profiling.sampling import' in line:
            m = re.match(r'^from profiling\.sampling import (.+)$', line)
            if m:
                names = m.group(1)
                new_lines.append("try:")
                new_lines.append(f"    from profiling.sampling import {names}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    pass  # profiling.sampling not available before Python 3.15")
            else:
                new_lines.append(line)
        elif 'import profiling' in line:
            new_lines.append("try:")
            new_lines.append(f"    {line}")
            new_lines.append("except ImportError:")
            new_lines.append("    import cProfile as profiling  # py38 compat")
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_typing_315_plus(content):
    typing_315_names = {"TypeForm", "Disjoint"}
    if "from typing import" not in content:
        return content

    modified = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        m = re.match(r'^from typing import (.+)$', line)
        if m:
            items = [x.strip() for x in m.group(1).split(',')]
            py38_items = []
            new_items = []
            for item in items:
                base_name = item.split(" as ")[0].split("[")[0].split(".")[0].strip()
                if base_name in typing_315_names:
                    new_items.append(item)
                else:
                    py38_items.append(item)
            if new_items:
                modified = True
                if py38_items:
                    new_lines.append("from typing import " + ", ".join(py38_items))
                for item in new_items:
                    as_match = re.match(r'(\w+)\s+as\s+(\w+)', item)
                    if as_match:
                        orig_name = as_match.group(1)
                        alias_name = as_match.group(2)
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {orig_name} as {alias_name}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {orig_name} as {alias_name}")
                    else:
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {item}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {item}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_dbm_sqlite3(content):
    if "dbm.sqlite3" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'from dbm.sqlite3 import' in line:
            m = re.match(r'^from dbm\.sqlite3 import (.+)$', line)
            if m:
                names = m.group(1)
                new_lines.append("try:")
                new_lines.append(f"    from dbm.sqlite3 import {names}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    from dbm import {names}  # py38 compat fallback")
            else:
                new_lines.append(line)
        elif 'import dbm.sqlite3' in line:
            new_lines.append("try:")
            new_lines.append("    import dbm.sqlite3")
            new_lines.append("except ImportError:")
            new_lines.append("    import dbm  # py38 compat fallback")
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_typing_313_plus(content):
    modified = False

    typing_313_names = {"ReadOnly", "TypeIs"}
    if "from typing import" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        m = re.match(r'^from typing import (.+)$', line)
        if m:
            items = [x.strip() for x in m.group(1).split(',')]
            py38_items = []
            new_items = []
            for item in items:
                base_name = item.split(" as ")[0].split("[")[0].split(".")[0].strip()
                if base_name in typing_313_names:
                    new_items.append(item)
                else:
                    py38_items.append(item)
            if new_items:
                modified = True
                if py38_items:
                    new_lines.append("from typing import " + ", ".join(py38_items))
                for item in new_items:
                    as_match = re.match(r'(\w+)\s+as\s+(\w+)', item)
                    if as_match:
                        orig_name = as_match.group(1)
                        alias_name = as_match.group(2)
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {orig_name} as {alias_name}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {orig_name} as {alias_name}")
                    else:
                        new_lines.append("try:")
                        new_lines.append(f"    from typing import {item}")
                        new_lines.append("except ImportError:")
                        new_lines.append(f"    from typing_extensions import {item}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_warnings_deprecated(content):
    if "warnings.deprecated" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'warnings.deprecated' in line and '_warnings_deprecated_compat' not in line:
            line = line.replace('warnings.deprecated', '_warnings_deprecated_compat')
        new_lines.append(line)

    if '_warnings_deprecated_compat' not in content:
        compat_code = (
            "try:\n"
            "    from warnings import deprecated as _warnings_deprecated_compat\n"
            "except ImportError:\n"
            "    def _warnings_deprecated_compat(msg, stacklevel=1):\n"
            "        def decorator(func):\n"
            "            import functools\n"
            "            @functools.wraps(func)\n"
            "            def wrapper(*args, **kwargs):\n"
            "                import warnings\n"
            "                warnings.warn(msg, DeprecationWarning, stacklevel=stacklevel + 1)\n"
            "                return func(*args, **kwargs)\n"
            "            return wrapper\n"
            "        return decorator\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_copy_replace(content):
    if "copy.replace" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'copy.replace(' in line and '_copy_replace_compat' not in line:
            line = line.replace('copy.replace(', '_copy_replace_compat(')
        new_lines.append(line)

    if '_copy_replace_compat' not in content:
        compat_code = (
            "try:\n"
            "    from copy import replace as _copy_replace_compat\n"
            "except ImportError:\n"
            "    def _copy_replace_compat(obj, /, **changes):\n"
            "        import copy\n"
            "        new_obj = copy.copy(obj)\n"
            "        for k, v in changes.items():\n"
            "            setattr(new_obj, k, v)\n"
            "        return new_obj\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_pep594_removed_modules(content):
    removed_modules = {
        'aifc': None,
        'audioop': None,
        'cgi': 'cgi' if sys.version_info >= (3, 13) else None,
        'cgitb': None,
        'chunk': None,
        'crypt': None,
        'imghdr': None,
        'mailcap': None,
        'msilib': None,
        'nis': None,
        'nntplib': None,
        'ossaudiodev': None,
        'pipes': None,
        'sndhdr': None,
        'spwd': None,
        'sunau': None,
        'telnetlib': 'telnetlib' if sys.version_info >= (3, 13) else None,
        'uu': None,
        'xdrlib': None,
        'lib2to3': None,
    }

    needs_fix = False
    for mod in removed_modules:
        if re.search(rf'\bimport {mod}\b', content) or re.search(rf'\bfrom {mod}\b', content):
            needs_fix = True
            break

    if not needs_fix:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            new_lines.append(line)
            continue

        for mod in removed_modules:
            from_m = re.match(rf'^(from {mod}\b.*)$', line)
            import_m = re.match(rf'^(import {mod}\b.*)$', line)
            if from_m or import_m:
                orig = line
                new_lines.append("try:")
                new_lines.append(f"    {orig}")
                new_lines.append("except ImportError:")
                new_lines.append(f"    pass  # {mod} removed in Python 3.13 (PEP 594)")
                line = None
                break
        if line is not None:
            new_lines.append(line)

    return '\n'.join(new_lines)


def fix_base64_z85(content):
    if "base64.z85" not in content:
        return content

    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'base64.z85encode(' in line and '_base64_z85encode_compat' not in line:
            line = line.replace('base64.z85encode(', '_base64_z85encode_compat(')
        if 'base64.z85decode(' in line and '_base64_z85decode_compat' not in line:
            line = line.replace('base64.z85decode(', '_base64_z85decode_compat(')
        new_lines.append(line)

    if '_base64_z85encode_compat' not in content:
        compat_code = (
            "try:\n"
            "    from base64 import z85encode as _base64_z85encode_compat\n"
            "    from base64 import z85decode as _base64_z85decode_compat\n"
            "except ImportError:\n"
            "    def _base64_z85encode_compat(data):\n"
            "        import base64\n"
            "        import struct\n"
            "        z85_chars = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#'\n"
            "        if len(data) % 4 != 0:\n"
            "            raise ValueError('z85encode data length must be multiple of 4')\n"
            "        result = bytearray()\n"
            "        for i in range(0, len(data), 4):\n"
            "            value = struct.unpack('>I', data[i:i+4])[0]\n"
            "            for j in range(4, -1, -1):\n"
            "                result.append(z85_chars[value // (85 ** j) % 85])\n"
            "        return bytes(result)\n"
            "    def _base64_z85decode_compat(data):\n"
            "        import struct\n"
            "        z85_chars = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#'\n"
            "        z85_map = {c: i for i, c in enumerate(z85_chars)}\n"
            "        if len(data) % 5 != 0:\n"
            "            raise ValueError('z85decode data length must be multiple of 5')\n"
            "        result = bytearray()\n"
            "        for i in range(0, len(data), 5):\n"
            "            value = 0\n"
            "            for c in data[i:i+5]:\n"
            "                value = value * 85 + z85_map[c]\n"
            "            result.extend(struct.pack('>I', value))\n"
            "        return bytes(result)\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_tomllib(content):
    if "import tomllib" not in content and "from tomllib" not in content:
        return content

    if re.search(r"try:\s*\n\s*(?:import|from) tomllib", content):
        return content

    if "tomli" in content:
        return content

    content = re.sub(
        r"^(\s*)import tomllib(\s+as\s+\w+)?\n",
        lambda m: f"{m.group(1)}try:\n{m.group(1)}    import tomllib{m.group(2) or ''}\n{m.group(1)}except ImportError:\n{m.group(1)}    import tomli as tomllib\n",
        content,
        flags=re.MULTILINE,
    )

    lines = content.split("\n")
    new_lines = []
    for line in lines:
        m = re.match(r"^(\s*)from tomllib import (.+)$", line)
        if m:
            indent = m.group(1)
            items = [item.strip() for item in m.group(2).split(",")]
            for item in items:
                new_lines.append(f"{indent}try:")
                new_lines.append(f"{indent}    from tomllib import {item}")
                new_lines.append(f"{indent}except ImportError:")
                new_lines.append(f"{indent}    from tomli import {item}")
        else:
            new_lines.append(line)

    return "\n".join(new_lines)


def fix_exception_group(content):
    if "ExceptionGroup" not in content:
        return content
    if re.search(r"try:\s*\n\s*(?:from exceptions import|import exceptiongroup)", content, re.IGNORECASE):
        return content

    if re.search(r"^from builtins import.*ExceptionGroup", content, re.MULTILINE):
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if 'ExceptionGroup' in line and 'exceptiongroup' not in line.lower() and '_ExceptionGroup_compat' not in line:
            if re.search(r'\bExceptionGroup\b', line) and not line.strip().startswith('#'):
                if 'from builtins import' not in line and 'import exceptiongroup' not in line:
                    line = re.sub(r'\bExceptionGroup\b', 'BaseExceptionGroup if hasattr(__builtins__, "ExceptionGroup") else __import__("exceptiongroup").BaseExceptionGroup', line)
                    needs_compat = True
        new_lines.append(line)

    return '\n'.join(new_lines)


def fix_add_note(content):
    if ".add_note(" not in content:
        return content

    needs_compat = False
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if '.add_note(' in line and '_add_note_compat' not in line:
            new_line = re.sub(r'(\w+)\.add_note\(', r'_add_note_compat(\1, ', line)
            if new_line != line:
                needs_compat = True
                line = new_line
        new_lines.append(line)

    if needs_compat and '_add_note_compat' not in content:
        compat_code = (
            "def _add_note_compat(exc, note):\n"
            "    if not hasattr(exc, '__notes__'):\n"
            "        exc.__notes__ = []\n"
            "    exc.__notes__.append(note)\n"
        )
        insert_pos = _find_compat_insert_position(new_lines)
        new_lines.insert(insert_pos, compat_code.rstrip())

    return '\n'.join(new_lines)


def fix_taskgroup(content):
    if "TaskGroup" not in content:
        return content
    if "asyncio" not in content:
        return content

    if re.search(r"try:\s*\n\s*from asyncio import TaskGroup", content):
        return content

    content = re.sub(
        r"^from asyncio import (.*)\bTaskGroup\b(.*)$",
        r"try:\n    from asyncio import TaskGroup\1\2\nexcept ImportError:\n    from asyncio_taskgroup import TaskGroup  # py38 compat",
        content,
        flags=re.MULTILINE,
    )

    return content


def fix_setup_py(root):
    setup_path = os.path.join(root, "setup.py")
    if not os.path.exists(setup_path):
        return False

    with open(setup_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    original = content

    content = re.sub(
        r'SUPPORTED_PYTHON_VERSIONS\s*=\s*\(\s*(?:9|1[0-9])\s*,',
        'SUPPORTED_PYTHON_VERSIONS = (8,',
        content,
    )
    content = re.sub(
        r'python_min_version\s*=\s*\(\s*3\s*,\s*(?:9|1[0-9])\s*,',
        'python_min_version = (3, 8,',
        content,
    )
    content = re.sub(
        r'"python>=3\.(?:9|1[0-9])(?:\.0)?"',
        '"python>=3.8.0"',
        content,
    )
    content = re.sub(
        r"python_requires\s*=\s*[\"']>=3\.(?:9|1[0-9])(?:\.\d+)?[\"']",
        'python_requires=">=3.8"',
        content,
    )

    if content != original:
        with open(setup_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        return True
    return False


def fix_pyproject_toml(root):
    pyproject_path = os.path.join(root, "pyproject.toml")
    if not os.path.exists(pyproject_path):
        return False

    with open(pyproject_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    original = content

    content = re.sub(
        r'''requires-python\s*=\s*["']>=3\.(?:9|1[0-9])(?:\.\d+)?["']''',
        'requires-python = ">=3.8"',
        content,
    )
    content = re.sub(
        r'''target-version\s*=\s*["']py3(?:9|1[0-9])["']''',
        'target-version = "py38"',
        content,
    )
    content = re.sub(
        r"""target-version\s*=\s*\[['"]py3(?:9|1[0-9])['"]\]""",
        "target-version = ['py38']",
        content,
    )

    if content != original:
        with open(pyproject_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        return True
    return False


def fix_cmake_python_version(root):
    skip = SKIP_DIRS_NO_SITE if _should_skip_site_packages(root) else SKIP_DIRS
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

        content = re.sub(
            r'find_package\(Python\s+3\.(?:9|1[0-9])',
            'find_package(Python 3.8',
            content,
        )
        content = re.sub(
            r'PYTHON_MIN_VERSION\s+3\.(?:9|1[0-9])',
            'PYTHON_MIN_VERSION 3.8',
            content,
        )
        content = re.sub(
            r'VERSION\s+3\.(?:9|1[0-9])\.0',
            'VERSION 3.8.0',
            content,
        )
        content = re.sub(
            r'Python3\s+3\.(?:9|1[0-9])',
            'Python3 3.8',
            content,
        )

        if content != original:
            with open(cmake_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
            modified = True

    return modified


def fix_collections_abc_callable_subscript(content):
    if 'from collections.abc import' not in content:
        return content
    if 'Callable' not in content:
        return content

    m = re.search(r'from collections\.abc import (.+)', content)
    if not m:
        return content

    imports_str = m.group(1)
    imports = [i.strip() for i in imports_str.split(',')]

    if 'Callable' not in imports:
        return content

    has_future = 'from __future__ import annotations' in content

    needs_fix = False
    if 'TypeVar' in content and re.search(r'bound\s*=\s*Callable\[', content):
        needs_fix = True
    elif not has_future and 'Callable[' in content:
        needs_fix = True

    if not needs_fix:
        return content

    other_imports = [i for i in imports if i != 'Callable']

    if other_imports:
        new_abc_line = f'from collections.abc import {", ".join(other_imports)}'
    else:
        new_abc_line = None

    typing_match = re.search(r'from typing import (.+)', content)
    if typing_match:
        existing = typing_match.group(1)
        existing_items = [i.strip() for i in existing.split(',')]
        if 'Callable' not in existing_items:
            existing_items.append('Callable')
        new_typing_line = f'from typing import {", ".join(existing_items)}'
        content = content.replace(typing_match.group(0), new_typing_line)
    else:
        insert_after = new_abc_line or m.group(0)
        content = content.replace(m.group(0), insert_after + '\nfrom typing import Callable')
        if new_abc_line and new_abc_line != m.group(0):
            pass

    if other_imports:
        content = content.replace(
            f'from collections.abc import {imports_str}',
            new_abc_line
        )
    else:
        content = content.replace(m.group(0) + '\n', '')
        content = content.replace(m.group(0), '')

    return content


def fix_lru_cached_property(content):
    if 'from functools import lru_cached_property' not in content:
        return content
    if 'except ImportError' in content and 'lru_cached_property' in content:
        return content

    fallback = """try:
    from functools import lru_cached_property
except ImportError:
    from functools import lru_cache
    class lru_cached_property:
        def __init__(self, func):
            self.func = func
            self.attrname = func.__name__
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            val = self.func(obj)
            object.__setattr__(obj, self.attrname, val)
            return val"""

    content = content.replace('from functools import lru_cached_property', fallback)
    return content


def fix_cached_property_import(content):
    if '@cached_property' not in content:
        return content
    if re.search(r'from\s+functools\s+import\s+.*\bcached_property\b', content):
        return content
    if 'import cached_property' in content:
        return content

    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
            break

    lines.insert(insert_idx, 'from functools import cached_property')
    return '\n'.join(lines)


def fix_types_py39_aliases(content, filepath=""):
    basename = os.path.basename(filepath)
    if basename != '__init__.py':
        return content

    needs_patch = False
    for alias in ['GenericAlias', 'EllipsisType', 'NotImplementedType']:
        pattern = rf'from types import.*\b{alias}\b'
        if re.search(pattern, content):
            needs_patch = True
            break

    if not needs_patch:
        if 'from types import GenericAlias' in content:
            needs_patch = True
        elif 'types.GenericAlias' in content:
            needs_patch = True

    if not needs_patch:
        return content

    patch_code = """import types as _types
if not hasattr(_types, 'GenericAlias'):
    _types.GenericAlias = type(lambda x: x)
if not hasattr(_types, 'EllipsisType'):
    _types.EllipsisType = type(Ellipsis)
if not hasattr(_types, 'NotImplementedType'):
    _types.NotImplementedType = type(NotImplemented)
"""

    if 'import types as _types' in content:
        return content

    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''"):
            break

    for j, patch_line in enumerate(patch_code.strip().split('\n')):
        lines.insert(insert_idx + j, patch_line)

    return '\n'.join(lines)


def fix_dict_merge_operator_improved(content):
    if "|" not in content:
        return content

    lines = content.split("\n")
    new_lines = []
    in_triple_quote = False
    triple_quote_char = None

    for line in lines:
        stripped = line.strip()

        if in_triple_quote:
            new_lines.append(line)
            if triple_quote_char in line:
                count = line.count(triple_quote_char)
                if line.strip().startswith(triple_quote_char):
                    count -= 1
                if count % 2 == 1:
                    in_triple_quote = False
                    triple_quote_char = None
            continue

        is_docstring_line = False
        for q in ('"""', "'''"):
            if q in line:
                before = line.split(q)[0]
                if before.count('"') % 2 == 0 and before.count("'") % 2 == 0:
                    count = line.count(q)
                    if count == 1:
                        in_triple_quote = True
                        triple_quote_char = q
                    is_docstring_line = True
                    break

        if is_docstring_line:
            new_lines.append(line)
            continue

        if stripped.startswith("#"):
            new_lines.append(line)
            continue

        if "|" not in line:
            new_lines.append(line)
            continue

        if re.search(r'\bdef\b|\bclass\b|\bimport\b|\bfrom\b', stripped):
            new_lines.append(line)
            continue

        new_line = line
        new_line, did_fix_inplace = _fix_dict_inplace_merge_line(new_line)
        new_line, did_fix_merge = _fix_dict_merge_line_improved(new_line)

        new_lines.append(new_line)

    return "\n".join(new_lines)


def _fix_dict_merge_line_improved(line):
    if "|" not in line:
        return line, False

    if re.search(r'isinstance\s*\(|issubclass\s*\(', line):
        return line, False

    if re.search(r'\|\|', line):
        return line, False

    numpy_or_patterns = [
        r'\bnp\.\w+\(',
        r'\bnumpy\.\w+\(',
        r'\bxp\.\w+\(',
        r'\.isnan\(',
        r'\.isinf\(',
        r'\.zeros\(',
        r'\.ones\(',
        r'\.empty\(',
        r'\.full\(',
        r'\.bool_\b',
        r'\.astype\(',
        r'\.shape\b',
        r'\.dtype\b',
        r'\bmask\b',
        r'\bcond\b',
        r'\bnans\b',
        r'\blbv\b',
        r'\bubv\b',
        r'\bhdir\b',
        r'\bfixed_\w+\b',
        r'\bnpcond\b',
        r'\bxcond\b',
        r'\bmcond\b',
        r'\bncond\b',
        r'\bmncond\b',
        r'\bup\b',
        r'\bdown\b',
        r'\beither\b',
        r'\bworking\b',
    ]

    for pat in numpy_or_patterns:
        if re.search(pat, line):
            return line, False

    set_union_patterns = [
        r'\bfrozenset\(',
        r'\bset\(',
        r'_VERSIONS',
        r'_mask',
        r'_inf_mask',
    ]

    for pat in set_union_patterns:
        if re.search(pat, line):
            return line, False

    result = []
    i = 0
    fixed = False
    in_string = False
    is_raw = False
    string_char = None
    while i < len(line):
        if in_string:
            if line[i] == '\\' and not is_raw:
                result.append(line[i:i + 2])
                i += 2
                continue
            if line[i] == string_char:
                in_string = False
                result.append(line[i])
                i += 1
                continue
            result.append(line[i])
            i += 1
            continue

        if i + 1 < len(line) and line[i] in ('r', 'b', 'f', 'u') and line[i + 1] in ('"', "'"):
            in_string = True
            is_raw = (line[i] == 'r')
            string_char = line[i + 1]
            result.append(line[i:i + 2])
            i += 2
            continue

        if line[i] in ('"', "'"):
            in_string = True
            is_raw = False
            string_char = line[i]
            result.append(line[i])
            i += 1
            continue

        if line[i] == '|':
            if i + 1 < len(line) and line[i + 1] == '=':
                result.append(line[i:i + 2])
                i += 2
                continue

            if i > 0 and line[i - 1] == '|':
                result.append(line[i])
                i += 1
                continue

            if _is_type_annotation_context(line, i):
                result.append(line[i])
                i += 1
                continue

            left_start = _find_expr_start_reverse(result)
            right_end = _find_expr_end_forward(line, i + 1)

            if left_start is not None and right_end is not None:
                left_expr = ''.join(result[left_start:]).strip()
                right_expr = line[i + 1:right_end].strip()

                if left_expr and right_expr:
                    if _is_likely_dict_merge_improved(left_expr, right_expr):
                        replacement = f"{{**{left_expr}, **{right_expr}}}"
                        result[left_start:] = [replacement]
                        i = right_end
                        fixed = True
                        continue

            result.append(line[i])
            i += 1
        else:
            result.append(line[i])
            i += 1

    return ''.join(result), fixed


def _is_likely_dict_merge_improved(left_expr, right_expr):
    left = left_expr.strip()
    right = right_expr.strip()

    if _is_clearly_not_dict(left) or _is_clearly_not_dict(right):
        return False

    if _looks_like_set_literal(left) or _looks_like_set_literal(right):
        return False

    if _looks_like_dict_literal(left) or _looks_like_dict_literal(right):
        return True

    if re.match(r'^dict\(', left) or re.match(r'^dict\(', right):
        return True

    if _looks_like_dict_variable(left) and _looks_like_dict_variable(right):
        return True

    dict_returning_funcs = [
        'dict(', 'copy(', 'deepcopy(', 'json.loads(', 'eval(',
        'vars(', 'globals(', 'locals(', 'defaultdict(', 'OrderedDict(',
        'Counter(', 'ChainMap(',
    ]
    for func in dict_returning_funcs:
        if func in left or func in right:
            return True

    return False


def fix_future_import_position(content):
    if "from __future__" not in content:
        return content

    lines = content.split('\n')
    future_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^from __future__ import .*annotations', stripped):
            future_idx = i
            break

    if future_idx is None or future_idx == 0:
        return content

    if all(lines[j].strip() == '' or lines[j].strip().startswith('#') or lines[j].strip().startswith('#!') or lines[j].strip().startswith('# -*-') or lines[j].startswith('# coding:') or lines[j].startswith('# vim:') for j in range(future_idx)):
        return content

    future_line = lines.pop(future_idx)

    insert_pos = 0
    if lines and lines[0].startswith('#!'):
        insert_pos = 1

    lines.insert(insert_pos, future_line)

    return '\n'.join(lines)


def process_file(filepath):
    import py_compile
    import tempfile
    import shutil

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    original = content

    content = fix_lambda_decorator(content)
    content = fix_pep695_generic_class(content)
    content = fix_pep695_generic_function(content)
    content = fix_pep695_type_stmt(content)
    content = fix_typing_311_plus(content)
    content = fix_pep585_604(content)
    content = fix_removeprefix_removesuffix(content)
    content = fix_functools_cache(content)
    content = fix_importlib_metadata_import(content)
    content = fix_typing_imports(content)
    content = fix_annotated_import(content)
    content = fix_isinstance_union(content)
    content = fix_dict_merge_operator_improved(content)
    content = fix_math_lcm(content)
    content = fix_math_nextafter_ulp(content)
    content = fix_collections_abc_aliases(content)
    content = fix_collections_abc_callable_subscript(content)
    content = fix_random_randbytes(content)
    content = fix_ast_unparse(content)
    content = fix_bytes_removeprefix_removesuffix(content)
    content = fix_parenthesized_context_manager(content)
    content = fix_match_case(content)
    content = fix_zoneinfo(content)
    content = fix_graphlib(content)
    content = fix_zip_strict(content)
    content = fix_int_bit_count(content)
    content = fix_aiter_anext(content)
    content = fix_bisect_key(content)
    content = fix_dataclass_slots(content)
    content = fix_tomllib(content)
    content = fix_add_note(content)
    content = fix_taskgroup(content)
    content = fix_math_exp2_cbrt(content)
    content = fix_datetime_utc(content)
    content = fix_enum_strenum(content)
    content = fix_contextlib_chdir(content)
    content = fix_operator_call(content)
    content = fix_hashlib_file_digest(content)
    content = fix_itertools_batched(content)
    content = fix_pathlib_walk(content)
    content = fix_distutils_import(content)
    content = fix_typing_313_plus(content)
    content = fix_warnings_deprecated(content)
    content = fix_copy_replace(content)
    content = fix_pep594_removed_modules(content)
    content = fix_base64_z85(content)
    content = fix_compression_zstd(content)
    content = fix_concurrent_interpreters(content)
    content = fix_annotationlib(content)
    content = fix_frozendict(content)
    content = fix_sentinel(content)
    content = fix_profiling_module(content)
    content = fix_typing_315_plus(content)
    content = fix_dbm_sqlite3(content)
    content = fix_lru_cached_property(content)
    content = fix_cached_property_import(content)
    content = fix_types_py39_aliases(content, filepath)
    content = fix_future_import_position(content)

    if content != original:
        try:
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
            tmp.write(content)
            tmp.close()
            py_compile.compile(tmp.name, doraise=True)
            os.unlink(tmp.name)
        except py_compile.PyCompileError as e:
            os.unlink(tmp.name)
            print(f"  WARNING: {filepath} - syntax error after fix, reverting: {e}")
            return False

        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        return True
    return False


def main():
    if len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        root = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    skip_site = _should_skip_site_packages(root)

    print(f"Python 3.8 兼容性修复脚本 - Python 源码部分")
    print(f"=" * 60)
    print(f"工作目录: {root}")
    if skip_site:
        print(f"排除 site-packages 目录: 是（脚本不在 site-packages 内）")
    else:
        print(f"排除 site-packages 目录: 否（脚本在 site-packages 内）")
    print()

    print("[1/4] 修复 setup.py / pyproject.toml 中的 Python 版本约束...")
    config_modified = []
    if fix_setup_py(root):
        config_modified.append("setup.py")
    if fix_pyproject_toml(root):
        config_modified.append("pyproject.toml")
    if fix_cmake_python_version(root):
        config_modified.append("CMake files")
    if config_modified:
        print(f"  已修改: {', '.join(config_modified)}")
    else:
        print("  无需修改")

    print()
    print("[2/4] 扫描 Python 源文件...")
    py_files = find_py_files(root, skip_site_packages=skip_site)
    print(f"  找到 {len(py_files)} 个 Python 文件")

    print()
    print("[3/4] 修复 Python 3.9+ 语法和 API...")
    modified_count = 0
    modified_files = []
    for i, filepath in enumerate(py_files):
        if "fix_py38" in os.path.basename(filepath):
            continue
        relpath = os.path.relpath(filepath, root).replace("\\", "/")
        if "/cpython/" in relpath:
            continue
        try:
            if process_file(filepath):
                modified_count += 1
                relpath = os.path.relpath(filepath, root)
                modified_files.append(relpath)
        except Exception as e:
            relpath = os.path.relpath(filepath, root)
            print(f"  [ERROR] {relpath}: {e}")

    print(f"  已修改 {modified_count} 个文件")
    if modified_count <= 50:
        for f in modified_files:
            print(f"    - {f}")

    print()
    print("[4/4] 最终验证...")
    py_files_after = find_py_files(root, skip_site_packages=skip_site)

    all_clean = True

    import py_compile

    syntax_errors = []
    for filepath in py_files_after:
        relpath = os.path.relpath(filepath, root).replace("\\", "/")
        if "fix_py38" in os.path.basename(filepath):
            continue
        if "/cpython/" in relpath:
            continue
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            syntax_errors.append((relpath, str(e)[:120]))

    if syntax_errors:
        print(f"  [!] 语法编译错误: {len(syntax_errors)} 个文件")
        for relpath, err in syntax_errors:
            print(f"      {relpath}: {err}")
        all_clean = False
    else:
        print(f"  [OK] 语法编译检查: {len(py_files_after)} 个文件全部通过")

    checks = [
        (r"\.removeprefix\(|\.removesuffix\(", "str.removeprefix/removesuffix"),
        (r"from functools import.*\bcache\b[^d]|@functools\.cache\b|@cache\b", "functools.cache"),
        (r"isinstance\([^)]*\|[^)]*\)", "isinstance(x, A|B)"),
        (r"issubclass\([^)]*\|[^)]*\)", "issubclass(x, A|B)"),
        (r"^import importlib\.metadata", "import importlib.metadata (未修复)"),
        (r"^from typing import .*\bTypeAlias\b", "from typing import TypeAlias (未修复)"),
        (r"^from typing import .*\bTypeGuard\b", "from typing import TypeGuard (未修复)"),
        (r"^from typing import .*\bParamSpec\b", "from typing import ParamSpec (未修复)"),
        (r"^from typing import .*\bConcatenate\b", "from typing import Concatenate (未修复)"),
        (r"^from typing import .*\bAnnotated\b(?!.*try:)", "from typing import Annotated (未修复)"),
        (r"^import zoneinfo$", "import zoneinfo (未修复)"),
        (r"^import graphlib$", "import graphlib (未修复)"),
        (r"^type\s+\w+\s*(\[|=\s*)", "PEP 695 type 语句 (3.12+)"),
        (r"^class\s+\w+\[", "PEP 695 泛型类语法 (3.12+)"),
        (r"^\s*@lambda\b", "PEP 614 lambda 装饰器 (3.9+)"),
        (r"^\s+match\s+(?!https?://)\w+\s*:", "PEP 634 match/case (3.10+)"),
        (r"^\s+case\s+[\[{_0-9\"'].*:", "PEP 634 case 语句 (3.10+)"),
        (r"with\s*\([^)]*\)\s*as\s+\w+\s*:", "括号化上下文管理器 (3.10+)"),
        (r"^from typing import .*\bNotRequired\b(?!.*try:)", "typing.NotRequired (3.11+) 未兼容"),
        (r"^from collections\.abc import .*\bBuffer\b(?!.*try:)", "collections.abc.Buffer (3.12+) 未兼容"),
        (r"\bmath\.lcm\s*\(", "math.lcm (3.9+) 未修复"),
        (r"\bmath\.nextafter\s*\(", "math.nextafter (3.9+) 未修复"),
        (r"\bmath\.ulp\s*\(", "math.ulp (3.9+) 未修复"),
        (r"\bast\.unparse\s*\(", "ast.unparse (3.9+) 未修复"),
        (r"\brandom\.randbytes\b", "random.randbytes (3.9+) 未修复"),
        (r"^from collections import .*\b(Mapping|MutableMapping|Iterable|Iterator|Sequence|MutableSequence|Set|MutableSet|Callable|Container|Hashable|Sized|Collection|Reversible)\b", "collections.XXX → collections.abc.XXX (3.9+) 未修复"),
        (r"\bzip\s*\([^)]*strict\s*=\s*True", "zip(strict=True) (3.10+) 未修复"),
        (r"(?<!\w)([a-zA-Z_]\w*)\.bit_count\(\)", "int.bit_count() (3.10+) 未修复"),
        (r"\baiter\s*\(", "aiter() (3.10+) 未修复"),
        (r"\banext\s*\(", "anext() (3.10+) 未修复"),
        (r"\bbisect\w*\s*\([^)]*key\s*=", "bisect key= (3.10+) 未修复"),
        (r"@(?:dataclasses\.)?dataclass\([^)]*slots\s*=\s*True", "dataclass(slots=True) (3.10+) 未修复"),
        (r"\.add_note\(", "BaseException.add_note() (3.11+) 未修复"),
        (r"^\s*import tomllib\b", "tomllib (3.11+) 未修复"),
        (r"\bfrom asyncio import.*\bTaskGroup\b", "asyncio.TaskGroup (3.11+) 未修复"),
        (r"\bmath\.exp2\(", "math.exp2() (3.11+) 未修复"),
        (r"\bmath\.cbrt\(", "math.cbrt() (3.11+) 未修复"),
        (r"\bdatetime\.UTC\b", "datetime.UTC (3.11+) 未修复"),
        (r"\bcontextlib\.chdir\(", "contextlib.chdir() (3.11+) 未修复"),
        (r"\boperator\.call\(", "operator.call() (3.11+) 未修复"),
        (r"\bhashlib\.file_digest\(", "hashlib.file_digest() (3.11+) 未修复"),
        (r"\bitertools\.batched\(", "itertools.batched() (3.12+) 未修复"),
        (r"\bPath\.walk\(", "pathlib.Path.walk() (3.12+) 未修复"),
        (r"^from distutils\b(?!.*(?:try:|except))", "distutils import (3.12移除) 未修复"),
        (r"\bwarnings\.deprecated\b", "warnings.deprecated() (3.13+) 未修复"),
        (r"\bcopy\.replace\(", "copy.replace() (3.13+) 未修复"),
        (r"^from (aifc|audioop|cgi|cgitb|chunk|crypt|imghdr|mailcap|msilib|nis|nntplib|ossaudiodev|pipes|sndhdr|spwd|sunau|telnetlib|uu|xdrlib|lib2to3)\b", "PEP 594 已移除模块 (3.13) 未修复"),
        (r"\bbase64\.z85", "base64.z85encode/decode() (3.13+) 未修复"),
        (r"\bfrom compression import", "compression module (3.14+) 未修复"),
        (r"\bfrom concurrent\.interpreters import", "concurrent.interpreters (3.14+) 未修复"),
        (r"\bimport annotationlib\b(?!.*(?:try:|except|version_info))", "annotationlib (3.14+) 未修复"),
        (r"\bfrozendict\b", "frozendict (3.15+) 未修复"),
        (r"\bsentinel\s*\(", "sentinel() (3.15+) 未修复"),
        (r"\bfrom profiling[. ]", "profiling module (3.15+) 未修复"),
        (r"\bdbm\.sqlite3\b", "dbm.sqlite3 (3.15+) 未修复"),
    ]

    for pattern, desc in checks:
        count = 0
        for filepath in py_files_after:
            relpath = os.path.relpath(filepath, root).replace("\\", "/")
            if "/cpython/" in relpath or "fix_py38" in os.path.basename(filepath):
                continue
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
            if "from __future__ import annotations" in file_content and desc in ("isinstance(x, A|B)", "issubclass(x, A|B)"):
                continue
            if "tomli" in file_content and desc == "tomllib (3.11+) 未修复":
                continue
            if "setuptools" in file_content and desc == "distutils import (3.12移除) 未修复":
                if re.search(r'try:\s*\n\s*from distutils', file_content):
                    continue
            if "sys.version_info" in file_content and desc == "annotationlib (3.14+) 未修复":
                continue
            count += len(re.findall(pattern, file_content, re.MULTILINE))
        if count > 0:
            print(f"  [!] {desc}: 仍有 {count} 处残留")
            all_clean = False
        else:
            print(f"  [OK] {desc}: 已全部修复")

    print()
    if all_clean:
        print("所有 Python 3.9+ 特性已修复完成!")
    else:
        print("部分特性仍有残留，请人工检查上述标记的文件。")

    print()
    print("提示: 对于 C/C++ 源码中的 Python C API 兼容性问题，")
    print("      请运行 fix_py38_c.py 脚本。")


if __name__ == "__main__":
    main()
