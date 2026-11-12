import importlib.util
import io
import json
import zipfile
from datetime import date

import pytest

from jukebox.settings.migration import CURRENT_SETTINGS_SCHEMA_VERSION

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.export_router import build_export_router


def build_router(*, library_path="/missing/library.json", settings_path="/missing/settings.json"):
    return build_export_router(library_path=library_path, settings_path=settings_path, today=lambda: date(2026, 11, 11))


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_library_returns_the_library_file_as_stored_on_disk(get_route, tmp_path):
    library_file = tmp_path / "library.json"
    library_file.write_text('{"discs": {"tag-1": not even json', encoding="utf-8")
    router = build_router(library_path=str(library_file))
    route = get_route(router, "/api/v1/export/library", "GET")

    response = route.endpoint()

    assert response.path == str(library_file)
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == 'attachment; filename="library-2026-11-11.json"'


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_library_returns_404_when_the_library_file_does_not_exist(get_route, tmp_path):
    router = build_router(library_path=str(tmp_path / "library.json"))
    route = get_route(router, "/api/v1/export/library", "GET")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No library file to export."


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_settings_returns_the_settings_file_as_stored_on_disk(get_route, tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"schema_version": 0}', encoding="utf-8")
    router = build_router(settings_path=str(settings_file))
    route = get_route(router, "/api/v1/export/settings", "GET")

    response = route.endpoint()

    assert response.path == str(settings_file)
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == 'attachment; filename="settings-2026-11-11.json"'


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_settings_returns_404_when_the_settings_file_does_not_exist(get_route, tmp_path):
    router = build_router(settings_path=str(tmp_path / "settings.json"))
    route = get_route(router, "/api/v1/export/settings", "GET")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "No persisted settings file to export."


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_all_returns_both_files_as_stored_on_disk_in_a_dated_zip(get_route, tmp_path):
    library_file = tmp_path / "library.json"
    library_file.write_text('{"discs": {"tag-1": not even json', encoding="utf-8")
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"schema_version": 0}', encoding="utf-8")
    router = build_router(library_path=str(library_file), settings_path=str(settings_file))
    route = get_route(router, "/api/v1/export/all", "GET")

    response = route.endpoint()

    assert response.media_type == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="jukebox-backup-2026-11-11.zip"'
    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
        assert sorted(archive.namelist()) == ["library.json", "settings.json"]
        assert archive.read("library.json") == library_file.read_bytes()
        assert archive.read("settings.json") == settings_file.read_bytes()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_export_all_holds_the_default_documents_for_missing_files(get_route, tmp_path):
    router = build_router(library_path=str(tmp_path / "library.json"), settings_path=str(tmp_path / "settings.json"))
    route = get_route(router, "/api/v1/export/all", "GET")

    response = route.endpoint()

    with zipfile.ZipFile(io.BytesIO(response.body)) as archive:
        assert sorted(archive.namelist()) == ["library.json", "settings.json"]
        assert json.loads(archive.read("library.json")) == {"discs": {}}
        assert json.loads(archive.read("settings.json")) == {"schema_version": CURRENT_SETTINGS_SCHEMA_VERSION}
