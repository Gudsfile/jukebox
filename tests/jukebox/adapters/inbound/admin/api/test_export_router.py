import importlib.util
import json
from unittest.mock import MagicMock

import pytest

from jukebox.domain.entities import Disc, DiscMetadata

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.export_router import build_export_router
    from jukebox.settings.errors import SettingsError


def build_router(*, list_discs=None, settings_service=None):
    return build_export_router(
        list_discs=list_discs if list_discs is not None else MagicMock(),
        settings_service=settings_service if settings_service is not None else MagicMock(),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_library_returns_library_file_as_attachment(get_route):
    list_discs = MagicMock()
    list_discs.execute.return_value = {
        "tag-1": Disc(uri="spotify:album:1", metadata=DiscMetadata(artist="Artist", album="Album")),
    }
    router = build_router(list_discs=list_discs)
    route = get_route(router, "/api/v1/export/library", "GET")

    response = route.endpoint()

    assert response.headers["content-disposition"] == 'attachment; filename="library.json"'
    assert json.loads(response.body) == {
        "discs": {
            "tag-1": {
                "uri": "spotify:album:1",
                "metadata": {"artist": "Artist", "album": "Album", "track": None, "playlist": None},
                "option": {"shuffle": False},
            }
        }
    }


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_library_returns_500_on_unexpected_error(get_route):
    list_discs = MagicMock()
    list_discs.execute.side_effect = RuntimeError("disk failure")
    router = build_router(list_discs=list_discs)
    route = get_route(router, "/api/v1/export/library", "GET")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 500


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_settings_returns_persisted_settings_file_as_attachment(get_route):
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/export/settings", "GET")

    response = route.endpoint()

    assert response.headers["content-disposition"] == 'attachment; filename="settings.json"'
    assert json.loads(response.body) == {"schema_version": 1, "admin": {"api": {"port": 8100}}}


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_settings_returns_400_when_settings_file_is_invalid(get_route):
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.side_effect = SettingsError("Settings file is corrupted.")
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/export/settings", "GET")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Settings file is corrupted."
