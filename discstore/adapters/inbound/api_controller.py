from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import FastAPI
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `api_controller` module", "api", "discstore api")
    ) from e

from discstore.adapters.inbound.api import (
    CurrentTagStatusOutput,
    DiscInput,
    DiscOutput,
    SettingsPatchInput,
    SettingsResetInput,
    build_current_tag_router,
    build_discs_router,
    build_settings_router,
)
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.settings.service_protocols import SettingsService

__all__ = [
    "APIController",
    "CurrentTagStatusOutput",
    "DiscInput",
    "DiscOutput",
    "SettingsPatchInput",
    "SettingsResetInput",
]


class APIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_current_tag_status: GetCurrentTagStatus,
        settings_service: SettingsService,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_current_tag_status = get_current_tag_status
        self.settings_service = settings_service
        self.app = FastAPI(
            title="DiscStore API",
            description="API for managing Jukebox disc library",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self.register_routes()

    def register_routes(self):
        self.app.include_router(
            build_discs_router(
                add_disc=self.add_disc,
                list_discs=self.list_discs,
                remove_disc=self.remove_disc,
                edit_disc=self.edit_disc,
            )
        )
        self.app.include_router(build_current_tag_router(self.get_current_tag_status))
        self.app.include_router(build_settings_router(self.settings_service))
