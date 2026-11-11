import importlib.util
import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from jukebox.adapters.inbound.admin.api.backup_archive import build_backup_archive
from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.domain.entities import Disc, DiscMetadata, Library, LibraryImportSummary
from jukebox.domain.repositories import LibraryRepository
from jukebox.domain.use_cases import ImportLibrary, PreviewLibraryImport
from jukebox.settings.errors import ErrorCode, InvalidSettingsError, UnsupportedSettingsVersionError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.export_router import build_export_router
    from jukebox.adapters.inbound.admin.api.import_router import build_import_router

pytestmark = [
    pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed"),
    pytest.mark.anyio,
]

LIBRARY = Library(discs={"tag-1": Disc(uri="/music/one.mp3", metadata=DiscMetadata(artist="Artist"))})
SUMMARY = LibraryImportSummary(disc_count=1, added=["tag-1"], changed=[], removed=["tag-2"])


def build_router(*, library_repository=None, preview_library_import=None, import_library=None, settings_service=None):
    return build_import_router(
        library_repository=library_repository or create_autospec(LibraryRepository, instance=True, spec_set=True),
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


CURRENT_LIBRARY = b'{"discs": {"tag-old": {"uri": "/music/old.mp3", "metadata": {}}}}'
CURRENT_SETTINGS = b'{"schema_version": 1}'
ARCHIVE = build_backup_archive(
    LIBRARY.model_dump_json().encode(), b'{"schema_version": 1, "admin": {"api": {"port": 8100}}}'
)


def build_archive_router(tmp_path, *, current_library: bytes | None = CURRENT_LIBRARY):
    library_file = tmp_path / "library.json"
    if current_library is not None:
        library_file.write_bytes(current_library)
    settings_file = tmp_path / "settings.json"
    settings_file.write_bytes(CURRENT_SETTINGS)
    repository = JsonLibraryAdapter(str(library_file))
    router = build_router(
        library_repository=repository,
        preview_library_import=PreviewLibraryImport(repository),
        import_library=ImportLibrary(repository),
        settings_service=SettingsService(repository=FileSettingsRepository(str(settings_file))),
    )
    return router, library_file, settings_file


async def test_preview_all_summarizes_both_files_without_writing(get_route, tmp_path):
    router, library_file, settings_file = build_archive_router(tmp_path)
    route = get_route(router, "/api/v1/import/all/preview", "POST")

    response = await route.endpoint(build_request(ARCHIVE))

    assert response["library"] == {"disc_count": 1, "added": ["tag-1"], "changed": [], "removed": ["tag-old"]}
    assert response["settings"]["updated_paths"] == ["admin.api.port"]
    assert library_file.read_bytes() == CURRENT_LIBRARY
    assert settings_file.read_bytes() == CURRENT_SETTINGS


async def test_import_all_replaces_both_files(get_route, tmp_path):
    router, library_file, settings_file = build_archive_router(tmp_path)
    route = get_route(router, "/api/v1/import/all", "POST")

    response = await route.endpoint(build_request(ARCHIVE))

    assert Library.model_validate_json(library_file.read_bytes()) == LIBRARY
    assert json.loads(settings_file.read_text()) == {"schema_version": 1, "admin": {"api": {"port": 8100}}}
    assert response["library"]["disc_count"] == 1
    assert response["settings"]["message"] == "Settings imported. Changes take effect after restart."


@pytest.mark.parametrize("path", ["/api/v1/import/all/preview", "/api/v1/import/all"])
@pytest.mark.parametrize(
    "body,detail",
    [
        pytest.param(b"not a zip", "The file is not a zip archive.", id="not_a_zip"),
        pytest.param(
            build_backup_archive(b'{"discs": ', CURRENT_SETTINGS),
            "library.json: The file is not valid JSON",
            id="library_not_json",
        ),
        pytest.param(
            build_backup_archive(b'{"discs": {"t": {}}}', CURRENT_SETTINGS),
            "library.json: Invalid library file",
            id="invalid_library",
        ),
        pytest.param(
            build_backup_archive(LIBRARY.model_dump_json().encode(), b"nope"),
            "settings.json: The file is not valid JSON",
            id="settings_not_json",
        ),
        pytest.param(
            build_backup_archive(LIBRARY.model_dump_json().encode(), b'{"schema_version": 7}'),
            "settings.json: Unsupported settings schema_version 7",
            id="invalid_settings",
        ),
    ],
)
async def test_invalid_archive_is_rejected_and_nothing_is_written(get_route, tmp_path, path, body, detail):
    router, library_file, settings_file = build_archive_router(tmp_path)
    route = get_route(router, path, "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(body))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail.startswith(detail)
    assert library_file.read_bytes() == CURRENT_LIBRARY
    assert settings_file.read_bytes() == CURRENT_SETTINGS


@pytest.mark.parametrize(
    "current_library",
    [
        pytest.param(CURRENT_LIBRARY, id="valid"),
        pytest.param(b'{"discs": {"tag-old": not even json', id="corrupted"),
    ],
)
async def test_import_all_puts_the_library_file_back_when_writing_the_settings_fails(
    get_route, tmp_path, mocker, current_library
):
    router, library_file, settings_file = build_archive_router(tmp_path, current_library=current_library)
    mocker.patch.object(FileSettingsRepository, "save_persisted_settings_data", side_effect=OSError("disk full"))
    route = get_route(router, "/api/v1/import/all", "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(ARCHIVE))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Server error: disk full"
    assert library_file.read_bytes() == current_library
    assert settings_file.read_bytes() == CURRENT_SETTINGS


async def test_import_all_removes_the_library_file_again_when_there_was_none(get_route, tmp_path, mocker):
    router, library_file, _ = build_archive_router(tmp_path, current_library=None)
    mocker.patch.object(FileSettingsRepository, "save_persisted_settings_data", side_effect=OSError("disk full"))
    route = get_route(router, "/api/v1/import/all", "POST")

    with pytest.raises(HTTPException):
        await route.endpoint(build_request(ARCHIVE))

    assert not library_file.exists()


async def test_import_all_reports_a_library_replaced_without_the_settings_when_the_rollback_fails(
    get_route, tmp_path, mocker, caplog
):
    router, _, settings_file = build_archive_router(tmp_path)
    mocker.patch.object(FileSettingsRepository, "save_persisted_settings_data", side_effect=OSError("disk full"))
    mocker.patch(
        "jukebox.adapters.outbound.json_library_adapter.JsonLibraryAdapter.restore",
        side_effect=OSError("read-only file system"),
    )
    route = get_route(router, "/api/v1/import/all", "POST")

    with pytest.raises(HTTPException) as exc_info:
        await route.endpoint(build_request(ARCHIVE))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == (
        "The library was replaced but the settings were not: disk full. "
        "Putting the previous library back failed: read-only file system"
    )
    assert "Could not put the previous library back" in caplog.text
    assert settings_file.read_bytes() == CURRENT_SETTINGS


async def test_exported_archive_can_be_imported_as_is(get_route, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    JsonLibraryAdapter(str(source / "library.json")).replace_library(LIBRARY)
    (source / "settings.json").write_bytes(b'{"schema_version": 1, "admin": {"api": {"port": 8100}}}')
    export_route = get_route(
        build_export_router(
            str(source / "library.json"), str(source / "settings.json"), today=lambda: date(2026, 11, 11)
        ),
        "/api/v1/export/all",
        "GET",
    )
    target_library = JsonLibraryAdapter(str(tmp_path / "library.json"))
    target_settings = tmp_path / "settings.json"
    router = build_router(
        library_repository=target_library,
        preview_library_import=PreviewLibraryImport(target_library),
        import_library=ImportLibrary(target_library),
        settings_service=SettingsService(repository=FileSettingsRepository(str(target_settings))),
    )
    import_route = get_route(router, "/api/v1/import/all", "POST")

    await import_route.endpoint(build_request(export_route.endpoint().body))

    assert json.loads((tmp_path / "library.json").read_text()) == json.loads((source / "library.json").read_text())
    assert json.loads(target_settings.read_text()) == json.loads((source / "settings.json").read_text())
