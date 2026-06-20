import pytest

from .helpers import SRC, find_private_import_violations

DOMAIN_MODULES = [
    "jukebox.domain.entities",
    "jukebox.domain.ports",
    "jukebox.domain.repositories",
    pytest.param(
        "jukebox.domain.use_cases",
        marks=pytest.mark.xfail(
            reason=(
                "library/ use cases not re-exported from use_cases/__init__.py; "
                "adapters and composition roots also import sub-modules directly"
            ),
            strict=True,
        ),
    ),
]


@pytest.mark.parametrize("module", DOMAIN_MODULES)
def test_domain_public_api_only(module: str) -> None:
    subpackage = module.removeprefix("jukebox.")
    violations = find_private_import_violations(
        SRC,
        module,
        allowed_dirs=[SRC / subpackage.replace(".", "/")],
    )
    if violations:
        pytest.fail(f"Imports must go through '{module}' only.\n\n" + "\n".join(sorted(violations)))
