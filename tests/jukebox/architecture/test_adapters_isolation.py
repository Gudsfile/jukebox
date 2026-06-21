import ast

import pytest

from .helpers import SRC, collect_import_lines

ADAPTERS_DIR = SRC / "adapters"
INBOUND_PREFIX = "jukebox.adapters.inbound"
OUTBOUND_PREFIX = "jukebox.adapters.outbound"

COMPOSITION_ROOTS = {
    SRC / "di_container.py",
    SRC / "admin" / "di_container.py",
    SRC / "app.py",
}


def find_external_adapter_violations() -> list[str]:
    violations: list[str] = []
    for py_file in SRC.rglob("*.py"):
        if py_file in COMPOSITION_ROOTS:
            continue
        if py_file.is_relative_to(ADAPTERS_DIR):
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for lineno, module in collect_import_lines(tree, "jukebox.adapters"):
            violations.append(f"{py_file}:{lineno} forbidden import from '{module}'")
    return violations


def find_cross_direction_violations() -> list[str]:
    violations: list[str] = []
    checks = [
        (ADAPTERS_DIR / "inbound", OUTBOUND_PREFIX),
        (ADAPTERS_DIR / "outbound", INBOUND_PREFIX),
    ]
    for scan_dir, forbidden_prefix in checks:
        for py_file in scan_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for lineno, module in collect_import_lines(tree, forbidden_prefix):
                violations.append(f"{py_file}:{lineno} forbidden import from '{module}'")
    return violations


def test_composition_roots_exist() -> None:
    missing = [str(p) for p in COMPOSITION_ROOTS if not p.exists()]
    if missing:
        pytest.fail(
            "COMPOSITION_ROOTS contains paths that do not exist. "
            "Update the list to reflect the current project structure.\n\n" + "\n".join(missing)
        )


@pytest.mark.xfail(reason="admin/pn532_command_handlers.py imports adapter directly", strict=True)
def test_only_composition_roots_import_adapters() -> None:
    violations = find_external_adapter_violations()
    if violations:
        pytest.fail("Only composition roots may import from adapters.\n\n" + "\n".join(sorted(violations)))


def test_adapters_no_cross_direction() -> None:
    violations = find_cross_direction_violations()
    if violations:
        pytest.fail("Inbound and outbound adapters must not import each other.\n\n" + "\n".join(sorted(violations)))
