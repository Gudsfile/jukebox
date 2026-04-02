from typing import Optional, Protocol

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict

from jukebox.settings.entities import (
    SelectedSonosGroupSettings,
    SelectedSonosSpeakerSettings,
)

from .discovery import DiscoveredSonosSpeaker
from .service import SonosService


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SonosSelectionAvailability(StrictModel):
    status: Literal["not_selected", "available", "unavailable"]
    speaker: Optional[DiscoveredSonosSpeaker] = None


class SonosSelectionStatus(StrictModel):
    selected_group: Optional[SelectedSonosGroupSettings] = None
    availability: SonosSelectionAvailability

    @property
    def selected_uid(self) -> Optional[str]:
        if self.selected_group is None:
            return None
        return self.selected_group.coordinator_uid


class SonosSelectionResult(StrictModel):
    speaker: DiscoveredSonosSpeaker
    selected_group: SelectedSonosGroupSettings
    settings_message: str
    restart_required: bool = False


class SaveSelectedSonosGroupResult(StrictModel):
    message: str = "Settings saved."
    restart_required: bool = False


class SelectedSonosGroupRepository(Protocol):
    def get_selected_group(self) -> Optional[SelectedSonosGroupSettings]: ...

    def save_selected_group(self, selected_group: SelectedSonosGroupSettings) -> SaveSelectedSonosGroupResult: ...


class SonosSelectionPlan(StrictModel):
    status: Literal["resolved", "needs_choice", "invalid_request", "none_available"]
    selected_uid: Optional[str] = None
    speakers: list[DiscoveredSonosSpeaker] = []
    error_message: Optional[str] = None


class PlanSonosSelection:
    def __init__(self, sonos_service: SonosService):
        self.sonos_service = sonos_service

    def execute(self, requested_uids: Optional[list[str]] = None) -> SonosSelectionPlan:
        available_speakers = self.sonos_service.list_available_speakers()
        if requested_uids is not None:
            if len(requested_uids) != 1:
                return SonosSelectionPlan(
                    status="invalid_request",
                    error_message="`uids` must contain exactly one UID in this phase.",
                )

            selected_uid = requested_uids[0]
            if selected_uid not in {speaker.uid for speaker in available_speakers}:
                return SonosSelectionPlan(
                    status="invalid_request",
                    error_message="Selected Sonos speaker is not currently discoverable: {}".format(selected_uid),
                )
            return SonosSelectionPlan(status="resolved", selected_uid=selected_uid)

        if not available_speakers:
            return SonosSelectionPlan(
                status="none_available",
                error_message="No visible Sonos speakers found.",
            )

        if len(available_speakers) == 1:
            return SonosSelectionPlan(status="resolved", selected_uid=available_speakers[0].uid)

        return SonosSelectionPlan(status="needs_choice", speakers=available_speakers)


class SaveSonosSelection:
    def __init__(self, selected_group_repository: SelectedSonosGroupRepository, sonos_service: SonosService):
        self.selected_group_repository = selected_group_repository
        self.sonos_service = sonos_service

    def execute(self, uid: str) -> SonosSelectionResult:
        speakers_by_uid = {speaker.uid: speaker for speaker in self.sonos_service.list_available_speakers()}
        speaker = speakers_by_uid.get(uid)
        if speaker is None:
            raise ValueError("Selected Sonos speaker is not currently discoverable: {}".format(uid))

        selected_group = SelectedSonosGroupSettings(
            coordinator_uid=uid,
            members=[SelectedSonosSpeakerSettings(uid=uid)],
        )
        settings_result = self.selected_group_repository.save_selected_group(selected_group)
        return SonosSelectionResult(
            speaker=speaker,
            selected_group=selected_group,
            settings_message=settings_result.message,
            restart_required=settings_result.restart_required,
        )


class GetSonosSelectionStatus:
    def __init__(self, selected_group_repository: SelectedSonosGroupRepository, sonos_service: SonosService):
        self.selected_group_repository = selected_group_repository
        self.sonos_service = sonos_service

    def execute(self) -> SonosSelectionStatus:
        selected_group = self.selected_group_repository.get_selected_group()
        if selected_group is None:
            return SonosSelectionStatus(
                selected_group=None,
                availability=SonosSelectionAvailability(status="not_selected", speaker=None),
            )

        available_speakers = {speaker.uid: speaker for speaker in self.sonos_service.list_available_speakers()}
        selected_speaker = available_speakers.get(selected_group.coordinator_uid)
        if selected_speaker is None:
            availability = SonosSelectionAvailability(status="unavailable", speaker=None)
        else:
            availability = SonosSelectionAvailability(status="available", speaker=selected_speaker)

        return SonosSelectionStatus(
            selected_group=selected_group,
            availability=availability,
        )
