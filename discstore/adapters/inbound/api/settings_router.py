from typing import Any, cast

from fastapi import APIRouter, HTTPException

from discstore.adapters.inbound.api.models import SettingsPatchInput, SettingsResetInput
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject


def build_settings_router(settings_service: SettingsService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["settings"])

    @router.get("/settings", summary="Get persisted settings")
    def get_settings() -> Any:
        try:
            return settings_service.get_persisted_settings_view()
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.get("/settings/effective", summary="Get effective settings")
    def get_effective_settings() -> Any:
        try:
            return settings_service.get_effective_settings_view()
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.patch("/settings", summary="Patch persisted settings")
    def patch_settings(patch: SettingsPatchInput) -> Any:
        try:
            return settings_service.patch_persisted_settings(cast(JsonObject, patch.root))
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.post("/settings/reset", summary="Reset a persisted setting")
    def reset_settings(payload: SettingsResetInput) -> Any:
        try:
            return settings_service.reset_persisted_value(payload.path)
        except SettingsError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    return router
