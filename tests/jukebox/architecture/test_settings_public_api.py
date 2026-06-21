import pytest

from .helpers import SRC, find_private_import_violations

PUBLIC_MODULE = "jukebox.settings"


@pytest.mark.xfail(reason="codebase imports settings sub-modules directly", strict=True)
def test_settings_public_api_only() -> None:
    violations = find_private_import_violations(
        SRC,
        PUBLIC_MODULE,
        allowed_dirs=[SRC / "settings"],
    )
    if violations:
        pytest.fail(f"Imports must go through '{PUBLIC_MODULE}' only.\n\n" + "\n".join(sorted(violations)))
