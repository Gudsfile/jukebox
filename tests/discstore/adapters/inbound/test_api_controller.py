import importlib.util
import sys
from unittest.mock import MagicMock

import pytest

if importlib.util.find_spec("fastapi") is not None:
    from discstore.adapters.inbound.api_controller import APIController
    from discstore.domain.entities import CurrentTagStatus


def test_dependencies_import_failure(mocker):
    sys.modules.pop("discstore.adapters.inbound.api_controller", None)
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert "The `api_controller` module requires the optional `api` dependencies." in str(err.value)
    assert "pip install 'gukebox[api]'" in str(err.value)
    assert "uv sync --extra api" in str(err.value)
    assert "uv run --extra api discstore api" in str(err.value)


@pytest.mark.skipif(importlib.util.find_spec("fastapi") is None, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("known_in_library", [True, False])
def test_get_current_disc_returns_current_disc_payload(known_in_library):
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(
        tag_id="tag-123", known_in_library=known_in_library
    )
    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-disc")

    response = route.endpoint()

    assert route.response_model.__name__ == "CurrentTagStatusOutput"
    assert response.model_dump() == {"tag_id": "tag-123", "known_in_library": known_in_library}
    controller.get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(importlib.util.find_spec("fastapi") is None, reason="FastAPI dependencies are not installed")
def test_get_current_disc_returns_no_content_when_absent():
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
    controller.get_current_tag_status.execute.return_value = None
    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-disc")

    response = route.endpoint()

    assert 204 in route.responses
    assert response.status_code == 204
    assert response.body == b""
    controller.get_current_tag_status.execute.assert_called_once_with()
