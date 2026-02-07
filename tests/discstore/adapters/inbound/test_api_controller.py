import pytest


def test_dependencies_import_failure(mocker):
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert (
        "The `api_controller` module requires FastAPI dependencies. Install them with: pip install gukebox[api]."
        in str(err.value)
    )
