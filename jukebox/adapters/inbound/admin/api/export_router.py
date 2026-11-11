import os
from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def _file_download(path: str, filename: str, missing_detail: str) -> FileResponse:
    # Serve the bytes as stored on disk: a backup must not be rebuilt from parsed (or migrated) data.
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=missing_detail)
    return FileResponse(path, media_type="application/json", filename=filename)


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

    return router
