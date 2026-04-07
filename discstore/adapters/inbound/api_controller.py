from typing import Any, Dict, Optional, cast

from pydantic import BaseModel, RootModel

from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import FastAPI, HTTPException, Response
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `api_controller` module", "api", "discstore api")
    ) from e

from discstore.domain.entities import CurrentTagStatus, Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.settings.entities import SelectedSonosGroupSettings
from jukebox.settings.errors import SettingsError
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject
from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError
from jukebox.sonos.selection import GetSonosSelectionStatus, PlanSonosSelection, SaveSonosSelection
from jukebox.sonos.service import SonosService


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class CurrentTagStatusOutput(CurrentTagStatus):
    pass


class SonosSpeakerOutput(DiscoveredSonosSpeaker):
    pass


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


class SettingsResetInput(BaseModel):
    path: str


class SettingsPatchInput(RootModel[Dict[str, Any]]):
    pass


class APIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_current_tag_status: GetCurrentTagStatus,
        settings_service: SettingsService,
        sonos_service: SonosService,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_current_tag_status = get_current_tag_status
        self.settings_service = settings_service
        self.sonos_service = sonos_service
        self.app = FastAPI(
            title="DiscStore API",
            description="API for managing Jukebox disc library",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self.register_routes()

    def register_routes(self):
        @self.app.get("/api/v1/discs", response_model=Dict[str, DiscOutput])
        def list_discs():
            return self.list_discs.execute()

        @self.app.get(
            "/api/v1/current-tag",
            response_model=CurrentTagStatusOutput,
            responses={204: {"description": "No current tag"}},
        )
        def get_current_tag():
            current_tag_status = self.get_current_tag_status.execute()
            if current_tag_status is None:
                return Response(status_code=204)

            return CurrentTagStatusOutput(**current_tag_status.model_dump())

        @self.app.get("/api/v1/sonos/speakers", response_model=list[SonosSpeakerOutput])
        def get_sonos_speakers():
            try:
                return self.sonos_service.list_available_speakers()
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
                plan = PlanSonosSelection(self.sonos_service).execute(
                    requested_uids=payload.uids,
                    coordinator_uid=payload.coordinator_uid,
                )
                if plan.status in {"invalid_request", "none_available"}:
                    raise HTTPException(status_code=400, detail=str(plan.error_message))
                if plan.status == "needs_choice" or plan.coordinator_uid is None:
                    raise HTTPException(status_code=400, detail="No Sonos speaker selection was made.")

                result = SaveSonosSelection(
                    SettingsSelectedSonosGroupRepository(self.settings_service),
                    self.sonos_service,
                ).execute(plan.selected_uids, coordinator_uid=plan.coordinator_uid)
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

        @self.app.get("/api/v1/settings")
        def get_settings():
            try:
                return self.settings_service.get_persisted_settings_view()
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.get("/api/v1/settings/effective")
        def get_effective_settings():
            try:
                return self.settings_service.get_effective_settings_view()
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.patch("/api/v1/settings")
        def patch_settings(patch: SettingsPatchInput):
            try:
                return self.settings_service.patch_persisted_settings(cast(JsonObject, patch.root))
            except SettingsError as err:
                raise HTTPException(status_code=400, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.post("/api/v1/settings/reset")
        def reset_settings(payload: SettingsResetInput):
            try:
                return self.settings_service.reset_persisted_value(payload.path)
            except SettingsError as err:
                raise HTTPException(status_code=400, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.post("/api/v1/disc", status_code=201)
        def add_or_edit_disc(tag_id: str, disc: DiscInput):
            try:
                self.add_disc.execute(tag_id, Disc(**disc.model_dump()))
                return {"message": "Disc added"}
            except ValueError:
                new_disc = Disc(**disc.model_dump())
                self.edit_disc.execute(tag_id, new_disc.uri, new_disc.metadata, new_disc.option)
                return {"message": "Disc edited"}
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.delete("/api/v1/disc", status_code=200)
        def remove_disc(tag_id: str):
            try:
                self.remove_disc.execute(tag_id)
                return {"message": "Disc removed"}
            except ValueError as value_err:
                raise HTTPException(status_code=404, detail=str(value_err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")
