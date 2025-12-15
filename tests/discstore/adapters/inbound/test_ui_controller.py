import sys
from unittest import mock

import pytest


def test_module_import_failure():
    version_below_py37 = (3, 7, 17, "final", 0)
    with mock.patch("sys.version_info", version_below_py37), pytest.raises(RuntimeError) as err:
        import discstore.adapters.inbound.ui_controller  # noqa: F401

    assert "The `ui_controller` module requires Python 3.10+." in str(err.value)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="FastUI requires Python 3.10+")
def test_dependencies_import_failure(mocker):
    mocker.patch.dict("sys.modules", {"fastui": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.ui_controller  # noqa: F401

    assert "The `ui_controller` module requires FastUI dependency. Install it with: pip install gukebox[ui]." in str(
        err.value
    )
