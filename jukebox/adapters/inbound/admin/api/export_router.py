import json
import os
from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from jukebox.adapters.inbound.admin.api.backup_archive import build_backup_archive
from jukebox.domain.entities import Library
from jukebox.settings.migration import CURRENT_SETTINGS_SCHEMA_VERSION

# A missing file is a normal state (settings never changed, no disc yet): the archive holds what the app reads then.
DEFAULT_LIBRARY = json.dumps(Library().model_dump(), indent=2).encode()
DEFAULT_SETTINGS = json.dumps({"schema_version": CURRENT_SETTINGS_SCHEMA_VERSION}, indent=2).encode()


def _file_download(path: str, filename: str, missing_detail: str) -> FileResponse:
    # Serve the bytes as stored on disk: a backup must not be rebuilt from parsed (or migrated) data.
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=missing_detail)
    return FileResponse(path, media_type="application/json", filename=filename)


def _read_file(path: str, default: bytes) -> bytes:
    try:
        with open(path, "rb") as file_obj:
            return file_obj.read()
    except FileNotFoundError:
        return default


def build_export_router(library_path: str, settings_path: str, today: Callable[[], date] = date.today) -> APIRouter:
    router = APIRouter(prefix="/api/v1/export", tags=["export"])

    @router.get("/library", summary="Download the library file")
    def export_library() -> FileResponse:
        return _file_download(library_path, f"library-{today().isoformat()}.json", "No library file to export.")

    @router.get("/settings", summary="Download the persisted settings file")
    def export_settings() -> FileResponse:
        return _file_download(
            settings_path, f"settings-{today().isoformat()}.json", "No persisted settings file to export."
        )

    @router.get("/all", summary="Download the library and the persisted settings files as one zip archive")
    def export_all() -> Response:
        archive = build_backup_archive(
            _read_file(library_path, DEFAULT_LIBRARY),
            _read_file(settings_path, DEFAULT_SETTINGS),
        )
        filename = f"jukebox-backup-{today().isoformat()}.zip"
        return Response(
            archive, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    return router
