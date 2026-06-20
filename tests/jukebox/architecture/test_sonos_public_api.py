import pytest

from .helpers import SRC, find_private_import_violations

PUBLIC_MODULE = "jukebox.sonos"


@pytest.mark.xfail(reason="codebase imports sonos sub-modules directly", strict=True)
def test_sonos_public_api_only() -> None:
    violations = find_private_import_violations(
        SRC,
        PUBLIC_MODULE,
        allowed_dirs=[SRC / "sonos"],
    )
    if violations:
        pytest.fail(f"Imports must go through '{PUBLIC_MODULE}' only.\n\n" + "\n".join(sorted(violations)))
