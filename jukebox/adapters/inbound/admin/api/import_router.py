import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from jukebox.domain.entities import Disc, Library, LibraryImportSummary
from jukebox.domain.use_cases import ImportLibrary, PreviewLibraryImport
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject, JsonValue

# The body is the uploaded file itself, read raw so that a file that is not JSON gets a clear 400.
_FILE_BODY: dict[str, Any] = {
    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}}
}


class _LibraryFile(BaseModel):
    """An uploaded library file: unlike a stored library, it must hold `discs` and nothing else.

    This keeps a settings file, picked by mistake, from replacing the library with an empty one.
    """

    model_config = ConfigDict(strict=True, extra="forbid")
    discs: dict[str, Disc]


async def _read_json_file(request: Request) -> JsonValue:
    try:
        return json.loads(await request.body())
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise HTTPException(status_code=400, detail=f"The file is not valid JSON: {err}")


async def _read_library_file(request: Request) -> Library:
    try:
        return Library(discs=_LibraryFile.model_validate(await _read_json_file(request)).discs)
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=f"Invalid library file: {err}")


def build_import_router(
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
        raw_data = await _read_json_file(request)
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
        raw_data = await _read_json_file(request)
        try:
            return settings_service.import_persisted_settings(raw_data)
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    return router
