from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from jukebox.domain.entities import Library
from jukebox.domain.use_cases import ListDiscs
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService


def _attachment(content: object, filename: str) -> JSONResponse:
    return JSONResponse(content=content, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def build_export_router(list_discs: ListDiscs, settings_service: SettingsService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/export", tags=["export"])

    @router.get("/library", summary="Download the library as library.json")
    def export_library() -> JSONResponse:
        try:
            library = Library(discs=list_discs.execute())
            return _attachment(library.model_dump(mode="json"), "library.json")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.get("/settings", summary="Download the persisted settings as settings.json")
    def export_settings() -> JSONResponse:
        try:
            return _attachment(settings_service.get_persisted_settings_view(), "settings.json")
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    return router
