from collections.abc import Callable

from fastapi import APIRouter
from pydantic import BaseModel

from jukebox.shared.config_utils import get_package_version


class VersionOutput(BaseModel):
    version: str


def build_version_router(get_version: Callable[[], str] = get_package_version) -> APIRouter:
    router = APIRouter(prefix="/api/v1/version", tags=["version"])

    @router.get("", summary="Get the installed version", response_model=VersionOutput)
    def get_installed_version() -> VersionOutput:
        return VersionOutput(version=get_version())

    return router
