import pytest

from .helpers import SRC, find_private_import_violations

DOMAIN_MODULES = [
    "jukebox.domain.entities",
    "jukebox.domain.ports",
    "jukebox.domain.repositories",
    "jukebox.domain.use_cases",
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
