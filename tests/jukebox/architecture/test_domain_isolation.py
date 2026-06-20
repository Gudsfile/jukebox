import ast

import pytest

from .helpers import SRC, collect_import_lines


def find_violations() -> list[str]:
    violations: list[str] = []
    for py_file in (SRC / "domain").rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for lineno, module in collect_import_lines(tree, "jukebox.adapters"):
            violations.append(f"{py_file}:{lineno} forbidden import from '{module}'")
    return violations


def test_domain_does_not_import_adapters() -> None:
    violations = find_violations()
    if violations:
        pytest.fail("Domain must not import from adapters.\n\n" + "\n".join(sorted(violations)))
