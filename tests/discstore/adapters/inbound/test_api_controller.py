import importlib.util
import sys
from typing import cast
from unittest.mock import MagicMock, create_autospec

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi.routing import APIRoute

    from discstore.adapters.inbound.api_controller import APIController
    from discstore.domain.entities import CurrentTagStatus
    from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus


def test_dependencies_import_failure(mocker):
    sys.modules.pop("discstore.adapters.inbound.api_controller", None)
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert "The `api_controller` module requires the optional `api` dependencies." in str(err.value)
    assert "pip install 'gukebox[api]'" in str(err.value)
    assert "uv sync --extra api" in str(err.value)
    assert "uv run --extra api discstore api" in str(err.value)


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("known_in_library", [True, False])
def test_get_current_tag_returns_current_tag_payload(known_in_library):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=known_in_library)
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), get_current_tag_status, MagicMock())
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-tag"),
    )

    response = route.endpoint()

    assert route.response_model is not None
    assert route.response_model.__name__ == "CurrentTagStatusOutput"
    assert response.model_dump() == {"tag_id": "tag-123", "known_in_library": known_in_library}
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), get_current_tag_status, MagicMock())
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-tag"),
    )

    response = route.endpoint()

    assert 204 in route.responses
    assert response.status_code == 204
    assert response.body == b""
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_settings_returns_sparse_settings_payload():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), settings_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/settings"),
    )

    response = route.endpoint()

    assert response == {"schema_version": 1}
    settings_service.get_persisted_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_effective_settings_returns_effective_settings_payload():
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {"settings": {}, "provenance": {}, "derived": {}}
    controller = APIController(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), settings_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/settings/effective"),
    )

    response = route.endpoint()

    assert response == {"settings": {}, "provenance": {}, "derived": {}}
    settings_service.get_effective_settings_view.assert_called_once_with()
