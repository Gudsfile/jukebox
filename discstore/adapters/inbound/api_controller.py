from typing import Optional

from pydantic import BaseModel

from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import FastAPI, HTTPException

    from discstore.adapters.inbound.api.current_tag_router import build_current_tag_router
    from discstore.adapters.inbound.api.discs_router import build_discs_router
    from discstore.adapters.inbound.api.models import (
        CurrentTagDiscOutput,
        CurrentTagStatusOutput,
        DiscInput,
        DiscOutput,
        DiscPatchInput,
        SettingsPatchInput,
        SettingsResetInput,
    )
    from discstore.adapters.inbound.api.settings_router import build_settings_router
except ModuleNotFoundError as e:
    if e.name != "fastapi":
        raise
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `api_controller` module", "api", "jukebox-admin api")
    ) from e
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.settings.entities import SelectedSonosGroupSettings
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError
from jukebox.sonos.selection import GetSonosSelectionStatus, SaveSonosSelection
from jukebox.sonos.service import SonosService

__all__ = [
    "APIController",
    "CurrentTagDiscOutput",
    "CurrentTagStatusOutput",
    "DiscInput",
    "DiscOutput",
    "DiscPatchInput",
    "SettingsPatchInput",
    "SettingsResetInput",
    "SonosSelectionInput",
]


class SonosSpeakerOutput(DiscoveredSonosSpeaker):
    pass


class SonosHouseholdOutput(BaseModel):
    household_id: str
    speakers: list[SonosSpeakerOutput]


class SelectedSonosGroupOutput(SelectedSonosGroupSettings):
    pass


class SonosSelectionMemberAvailabilityOutput(BaseModel):
    uid: str
    status: str
    speaker: Optional[SonosSpeakerOutput] = None


class SonosSelectionAvailabilityOutput(BaseModel):
    status: str
    members: list[SonosSelectionMemberAvailabilityOutput]


class SonosSelectionOutput(BaseModel):
    selected_group: Optional[SelectedSonosGroupOutput] = None
    availability: SonosSelectionAvailabilityOutput


class SonosSelectionInput(BaseModel):
    uids: list[str]
    coordinator_uid: Optional[str] = None


class SonosSelectionUpdateOutput(BaseModel):
    selected_group: SelectedSonosGroupOutput
    availability: SonosSelectionAvailabilityOutput
    message: str
    restart_required: bool


class APIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        get_current_tag_status: GetCurrentTagStatus,
        settings_service: SettingsService,
        sonos_service: SonosService,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_disc = get_disc
        self.get_current_tag_status = get_current_tag_status
        self.settings_service = settings_service
        self.sonos_service = sonos_service
        self.app = FastAPI(
            title="Jukebox Admin API",
            description="API for managing Jukebox disc library and settings",
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
                get_disc=self.get_disc,
            )
        )
        self.app.include_router(
            build_current_tag_router(
                get_current_tag_status=self.get_current_tag_status,
                add_disc=self.add_disc,
                edit_disc=self.edit_disc,
                get_disc=self.get_disc,
                remove_disc=self.remove_disc,
            )
        )
        self.app.include_router(build_settings_router(self.settings_service))

        @self.app.get("/api/v1/sonos/speakers", response_model=list[SonosSpeakerOutput])
        def get_sonos_speakers():
            try:
                return self.sonos_service.list_available_speakers()
            except SonosDiscoveryError as err:
                raise HTTPException(status_code=502, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.get("/api/v1/sonos/households", response_model=list[SonosHouseholdOutput])
        def get_sonos_households():
            try:
                return [
                    SonosHouseholdOutput(
                        household_id=household.household_id,
                        speakers=[SonosSpeakerOutput(**speaker.model_dump()) for speaker in household.speakers],
                    )
                    for household in self.sonos_service.list_selectable_households()
                ]
            except SonosDiscoveryError as err:
                raise HTTPException(status_code=502, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.get("/api/v1/sonos/selection", response_model=SonosSelectionOutput)
        def get_sonos_selection():
            try:
                return GetSonosSelectionStatus(
                    SettingsSelectedSonosGroupRepository(self.settings_service),
                    self.sonos_service,
                ).execute()
            except SonosDiscoveryError as err:
                raise HTTPException(status_code=502, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.put("/api/v1/sonos/selection", response_model=SonosSelectionUpdateOutput)
        def put_sonos_selection(payload: SonosSelectionInput):
            try:
                result = SaveSonosSelection(
                    SettingsSelectedSonosGroupRepository(self.settings_service),
                    self.sonos_service,
                ).execute(payload.uids, coordinator_uid=payload.coordinator_uid)
                return SonosSelectionUpdateOutput(
                    selected_group=SelectedSonosGroupOutput(**result.selected_group.model_dump()),
                    availability=SonosSelectionAvailabilityOutput(
                        status="available",
                        members=[
                            SonosSelectionMemberAvailabilityOutput(
                                uid=member.uid,
                                status="available",
                                speaker=SonosSpeakerOutput(**member.model_dump()),
                            )
                            for member in result.members
                        ],
                    ),
                    message=result.settings_message,
                    restart_required=result.restart_required,
                )
            except SonosDiscoveryError as err:
                raise HTTPException(status_code=502, detail=str(err))
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")
