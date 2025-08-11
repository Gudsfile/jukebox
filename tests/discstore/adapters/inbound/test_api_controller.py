import sys
from unittest import mock

import pytest


def test_module_import_failure():
    version_below_py37 = (3, 7, 17, "final", 0)
    with mock.patch("sys.version_info", version_below_py37):
        with pytest.raises(RuntimeError) as err:
            import discstore.adapters.inbound.api_controller  # noqa: F401

    assert "The `api_controller` module requires Python 3.8+." in str(err.value)


@pytest.mark.skipif(sys.version_info < (3, 8), reason="FastAPI requires Python 3.8+")
def test_dependencies_import_failure(mocker):
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert (
        "The `api_controller` module requires FastAPI dependencies. Install them with: pip install jukebox[api]."
        in str(err.value)
    )
