import importlib.util
import json
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from jukebox.domain.entities import Disc, DiscMetadata, Library, LibraryImportSummary
from jukebox.domain.use_cases import ImportLibrary, PreviewLibraryImport
from jukebox.settings.errors import ErrorCode, InvalidSettingsError, UnsupportedSettingsVersionError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.import_router import build_import_router

pytestmark = [
    pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed"),
    pytest.mark.anyio,
]

LIBRARY = Library(discs={"tag-1": Disc(uri="/music/one.mp3", metadata=DiscMetadata(artist="Artist"))})
SUMMARY = LibraryImportSummary(disc_count=1, added=["tag-1"], changed=[], removed=["tag-2"])


def build_router(*, preview_library_import=None, import_library=None, settings_service=None):
    return build_import_router(
        preview_library_import=preview_library_import
        or create_autospec(PreviewLibraryImport, instance=True, spec_set=True),
        import_library=import_library or create_autospec(ImportLibrary, instance=True, spec_set=True),
        settings_service=settings_service or MagicMock(),
    )


def build_request(body: bytes) -> MagicMock:
    request = MagicMock()
    request.body = AsyncMock(return_value=body)
    return request


async def test_preview_library_returns_summary_without_importing(get_route):
    preview_library_import = create_autospec(PreviewLibraryImport, instance=True, spec_set=True)
    preview_library_import.execute.return_value = SUMMARY
    import_library = create_autospec(ImportLibrary, instance=True, spec_set=True)
    router = build_router(preview_library_import=preview_library_import, import_library=import_library)
    route = get_route(router, "/api/v1/import/library/preview", "POST")

    response = await route.endpoint(build_request(LIBRARY.model_dump_json().encode()))

    assert response == SUMMARY
    preview_library_import.execute.assert_called_once_with(LIBRARY)
    import_library.execute.assert_not_called()


async def test_import_library_replaces_library_and_returns_summary(get_route):
    preview_library_import = create_autospec(PreviewLibraryImport, instance=True, spec_set=True)
    preview_library_import.execute.return_value = SUMMARY
    import_library = create_autospec(ImportLibrary, instance=True, spec_set=True)
    router = build_router(preview_library_import=preview_library_import, import_library=import_library)
    route = get_route(router, "/api/v1/import/library", "POST")

    response = await route.endpoint(build_request(LIBRARY.model_dump_json().encode()))

    assert response == SUMMARY
    import_library.execute.assert_called_once_with(LIBRARY)


@pytest.mark.parametrize("path", ["/api/v1/import/library/preview", "/api/v1/import/library"])
@pytest.mark.parametrize(
    "body,detail",
    [
        pytest.param(b'{"discs": ', "The file is not valid JSON", id="malformed_json"),
        pytest.param(b"\xff\xfe", "The file is not valid JSON", id="not_utf8"),
        pytest.param(b"[]", "Invalid library file", id="not_an_object"),
        pytest.param(b'{"discs": {"tag-1": {"metadata": {}}}}', "Invalid library file", id="missing_uri"),
        pytest.param(b"{}", "Invalid library file", id="missing_discs"),
        pytest.param(b'{"schema_version": 1, "admin": {}}', "Invalid library file", id="settings_file"),
        pytest.param(b'{"discs": {}, "extra": true}', "Invalid library file", id="unknown_key"),
    ],
)
async def test_invalid_library_file_is_rejected_and_nothing_is_written(get_route, path, body, detail):
    preview_library_import = create_autospec(PreviewLibraryImport, instance=True, spec_set=True)
    import_library = create_autospec(ImportLibrary, instance=True, spec_set=True)
    router = build_router(preview_library_import=preview_library_import, import_library=import_library)
    route = get_route(router, path, "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(body))

    assert exc_info.value.status_code == 400
    assert detail in exc_info.value.detail
    import_library.execute.assert_not_called()


async def test_exported_library_file_can_be_imported_as_is(get_route, tmp_path):
    from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter

    source = JsonLibraryAdapter(str(tmp_path / "source.json"))
    source.replace_library(LIBRARY)
    target = JsonLibraryAdapter(str(tmp_path / "target.json"))
    router = build_router(preview_library_import=PreviewLibraryImport(target), import_library=ImportLibrary(target))
    route = get_route(router, "/api/v1/import/library", "POST")

    await route.endpoint(build_request((tmp_path / "source.json").read_bytes()))

    assert json.loads((tmp_path / "target.json").read_text()) == json.loads((tmp_path / "source.json").read_text())


async def test_preview_settings_forwards_parsed_file_to_service(get_route):
    settings_service = MagicMock()
    settings_service.preview_settings_import.return_value = {"updated_paths": ["admin.api.port"]}
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/import/settings/preview", "POST")

    response = await route.endpoint(build_request(b'{"schema_version": 1, "admin": {"api": {"port": 8100}}}'))

    assert response == {"updated_paths": ["admin.api.port"]}
    settings_service.preview_settings_import.assert_called_once_with(
        {"schema_version": 1, "admin": {"api": {"port": 8100}}}
    )
    settings_service.import_persisted_settings.assert_not_called()


async def test_import_settings_forwards_parsed_file_to_service(get_route):
    settings_service = MagicMock()
    settings_service.import_persisted_settings.return_value = {"message": "Settings imported."}
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/import/settings", "POST")

    response = await route.endpoint(build_request(b'{"schema_version": 1}'))

    assert response == {"message": "Settings imported."}
    settings_service.import_persisted_settings.assert_called_once_with({"schema_version": 1})


@pytest.mark.parametrize("path", ["/api/v1/import/settings/preview", "/api/v1/import/settings"])
async def test_settings_file_that_is_not_json_is_rejected(get_route, path):
    settings_service = MagicMock()
    router = build_router(settings_service=settings_service)
    route = get_route(router, path, "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(b"not json"))

    assert exc_info.value.status_code == 400
    assert "The file is not valid JSON" in exc_info.value.detail
    settings_service.import_persisted_settings.assert_not_called()


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/import/settings/preview", "preview_settings_import"),
        ("/api/v1/import/settings", "import_persisted_settings"),
    ],
)
@pytest.mark.parametrize(
    "error",
    [
        InvalidSettingsError("Invalid settings file: bad", code=ErrorCode.INVALID_FILE),
        UnsupportedSettingsVersionError("Unsupported settings schema_version 99"),
    ],
)
async def test_invalid_settings_file_returns_400(get_route, path, method, error):
    settings_service = MagicMock()
    getattr(settings_service, method).side_effect = error
    router = build_router(settings_service=settings_service)
    route = get_route(router, path, "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(b'{"schema_version": 99}'))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == str(error)


async def test_settings_file_with_a_number_given_as_a_string_breaking_a_rule_returns_400(get_route, tmp_path):
    settings_file = tmp_path / "settings.json"
    router = build_router(settings_service=SettingsService(repository=FileSettingsRepository(str(settings_file))))
    route = get_route(router, "/api/v1/import/settings", "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(
            build_request(b'{"schema_version": 1, "jukebox": {"runtime": {"loop_interval_seconds": "1"}}}')
        )

    assert exc_info.value.status_code == 400
    assert "loop_interval_seconds must be lower than" in exc_info.value.detail
    assert not settings_file.exists()
