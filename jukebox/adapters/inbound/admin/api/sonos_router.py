from fastapi import APIRouter, HTTPException

from jukebox.adapters.inbound.admin.api.models import (
    SelectedSonosGroupOutput,
    SonosSelectionAvailabilityOutput,
    SonosSelectionInput,
    SonosSelectionMemberAvailabilityOutput,
    SonosSelectionOutput,
    SonosSelectionUpdateOutput,
    SonosSpeakerOutput,
)
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.sonos.discovery import SonosDiscoveryError
from jukebox.sonos.selection import GetSonosSelectionStatus, SaveSonosSelection
from jukebox.sonos.service import SonosService


def build_sonos_router(settings_service: SettingsService, sonos_service: SonosService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["sonos"])

    @router.get(
        "/sonos/speakers", response_model=list[SonosSpeakerOutput], summary="List Sonos speakers on the network"
    )
    def get_sonos_speakers():
        try:
            return sonos_service.list_network_speakers()
        except SonosDiscoveryError as err:
            raise HTTPException(status_code=502, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.get("/sonos/selection", response_model=SonosSelectionOutput, summary="Get the selected Sonos group")
    def get_sonos_selection():
        try:
            return GetSonosSelectionStatus(
                SettingsSelectedSonosGroupRepository(settings_service),
                sonos_service,
            ).execute()
        except SonosDiscoveryError as err:
            raise HTTPException(status_code=502, detail=str(err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    @router.put("/sonos/selection", response_model=SonosSelectionUpdateOutput, summary="Save the selected Sonos group")
    def put_sonos_selection(payload: SonosSelectionInput):
        try:
            result = SaveSonosSelection(
                SettingsSelectedSonosGroupRepository(settings_service),
                sonos_service,
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
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

    return router
