import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from jukebox.adapters.inbound.admin.api.backup_archive import (
    LIBRARY_ENTRY,
    SETTINGS_ENTRY,
    InvalidBackupArchiveError,
    read_backup_archive,
)
from jukebox.domain.entities import Disc, Library, LibraryImportSummary
from jukebox.domain.repositories import LibraryRepository
from jukebox.domain.use_cases import ImportLibrary, PreviewLibraryImport
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject, JsonValue

LOGGER = logging.getLogger("jukebox")

# The body is the uploaded file itself, read raw so that a file that is not JSON gets a clear 400.
_FILE_BODY: dict[str, Any] = {
    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}
}
_ARCHIVE_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}},
    }
}


class _LibraryFile(BaseModel):
    """An uploaded library file: unlike a stored library, it must hold `discs` and nothing else.

    This keeps a settings file, picked by mistake, from replacing the library with an empty one.
    """

    model_config = ConfigDict(strict=True, extra="forbid")
    discs: dict[str, Disc]


def _parse_json(content: bytes, source: str = "") -> JsonValue:
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise HTTPException(status_code=400, detail=f"{source}The file is not valid JSON: {err}")


def _parse_library(content: bytes, source: str = "") -> Library:
    try:
        return Library(discs=_LibraryFile.model_validate(_parse_json(content, source)).discs)
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=f"{source}Invalid library file: {err}")


async def _read_library_file(request: Request) -> Library:
    return _parse_library(await request.body())


def build_import_router(
    library_repository: LibraryRepository,
    preview_library_import: PreviewLibraryImport,
    import_library: ImportLibrary,
    settings_service: SettingsService,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/import", tags=["import"])

    @router.post(
        "/library/preview",
        response_model=LibraryImportSummary,
        summary="Validate a library file and summarize what importing it would change",
        openapi_extra=_FILE_BODY,
    )
    async def preview_library(request: Request) -> LibraryImportSummary:
        library = await _read_library_file(request)
        try:
            return preview_library_import.execute(library)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.post(
        "/library",
        response_model=LibraryImportSummary,
        summary="Replace the library with a library file",
        openapi_extra=_FILE_BODY,
    )
    async def import_library_file(request: Request) -> LibraryImportSummary:
        library = await _read_library_file(request)
        try:
            summary = preview_library_import.execute(library)
            import_library.execute(library)
            return summary
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.post(
        "/settings/preview",
        response_model=dict[str, Any],
        summary="Validate a settings file and list the settings importing it would change",
        openapi_extra=_FILE_BODY,
    )
    async def preview_settings(request: Request) -> JsonObject:
        raw_data = _parse_json(await request.body())
        try:
            return settings_service.preview_settings_import(raw_data)
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.post(
        "/settings",
        response_model=dict[str, Any],
        summary="Replace the persisted settings with a settings file",
        openapi_extra=_FILE_BODY,
    )
    async def import_settings(request: Request) -> JsonObject:
        raw_data = _parse_json(await request.body())
        try:
            return settings_service.import_persisted_settings(raw_data)
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    async def read_archive(request: Request) -> tuple[Library, JsonValue]:
        try:
            library_content, settings_content = read_backup_archive(await request.body())
        except InvalidBackupArchiveError as err:
            raise HTTPException(status_code=400, detail=str(err))
        library = _parse_library(library_content, f"{LIBRARY_ENTRY}: ")
        settings_data = _parse_json(settings_content, f"{SETTINGS_ENTRY}: ")
        return library, settings_data

    def preview_archive(library: Library, settings_data: JsonValue) -> JsonObject:
        try:
            settings_summary = settings_service.preview_settings_import(settings_data)
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=f"{SETTINGS_ENTRY}: {err}")
        return {
            "library": preview_library_import.execute(library).model_dump(mode="json"),
            "settings": settings_summary,
        }

    @router.post(
        "/all/preview",
        response_model=dict[str, Any],
        summary="Validate a backup archive and summarize what importing it would change",
        openapi_extra=_ARCHIVE_BODY,
    )
    async def preview_all(request: Request) -> JsonObject:
        library, settings_data = await read_archive(request)
        try:
            return preview_archive(library, settings_data)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.post(
        "/all",
        response_model=dict[str, Any],
        summary="Replace the library and the persisted settings with a backup archive",
        openapi_extra=_ARCHIVE_BODY,
    )
    async def import_all(request: Request) -> JsonObject:
        library, settings_data = await read_archive(request)
        try:
            # Validate both files before writing any of them.
            summary = preview_archive(library, settings_data)
            # Write both files or none: keep the library file as is, even corrupted, to put it back.
            previous_library = library_repository.snapshot()
            import_library.execute(library)
            try:
                summary["settings"] = settings_service.import_persisted_settings(settings_data)
            except Exception as err:
                try:
                    library_repository.restore(previous_library)
                except Exception as rollback_err:
                    LOGGER.exception("Could not put the previous library back")
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"The library was replaced but the settings were not: {err!s}. "
                            f"Putting the previous library back failed: {rollback_err!s}"
                        ),
                    )
                raise
            return summary
        except HTTPException:
            raise
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=f"{SETTINGS_ENTRY}: {err}")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    return router
