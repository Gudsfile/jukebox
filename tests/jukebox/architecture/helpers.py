import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "jukebox"


def collect_import_lines(tree: ast.Module, prefix: str) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(prefix):
                results.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefix):
                    results.append((node.lineno, alias.name))
    return results


def find_private_import_violations(
    src: Path,
    public_module: str,
    allowed_dirs: list[Path] | None = None,
) -> list[str]:
    private_prefix = f"{public_module}."
    violations: list[str] = []

    for py_file in src.rglob("*.py"):
        if any(py_file.is_relative_to(d) for d in (allowed_dirs or [])):
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for lineno, module in collect_import_lines(tree, private_prefix):
            violations.append(f"{py_file}:{lineno} forbidden import from '{module}'")

    return violations
