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


class SonosSelectionMemberAvailability(StrictModel):
    uid: str
    status: Literal["available", "unavailable"]
    speaker: Optional[DiscoveredSonosSpeaker] = None


class SonosSelectionAvailability(StrictModel):
    status: Literal["not_selected", "available", "partial", "unavailable"]
    members: list[SonosSelectionMemberAvailability] = []


class SonosSelectionStatus(StrictModel):
    selected_group: Optional[SelectedSonosGroupSettings] = None
    availability: SonosSelectionAvailability

    @property
    def selected_uid(self) -> Optional[str]:
        if self.selected_group is None:
            return None
        return self.selected_group.coordinator_uid


class SonosSelectionResult(StrictModel):
    coordinator: DiscoveredSonosSpeaker
    members: list[DiscoveredSonosSpeaker]
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
    selected_uids: list[str] = []
    coordinator_uid: Optional[str] = None
    speakers: list[DiscoveredSonosSpeaker] = []
    error_message: Optional[str] = None

    @property
    def selected_uid(self) -> Optional[str]:
        return self.coordinator_uid


class PlanSonosSelection:
    def __init__(self, sonos_service: SonosService):
        self.sonos_service = sonos_service

    def execute(
        self,
        requested_uids: Optional[list[str]] = None,
        coordinator_uid: Optional[str] = None,
    ) -> SonosSelectionPlan:
        available_speakers = self.sonos_service.list_available_speakers()
        if requested_uids is not None:
            try:
                validated_group = _validate_selection_request(
                    available_speakers=available_speakers,
                    requested_uids=requested_uids,
                    coordinator_uid=coordinator_uid,
                )
            except ValueError as err:
                return SonosSelectionPlan(status="invalid_request", error_message=str(err))
            return SonosSelectionPlan(
                status="resolved",
                selected_uids=validated_group.selected_uids,
                coordinator_uid=validated_group.coordinator_uid,
            )

        if not available_speakers:
            return SonosSelectionPlan(
                status="none_available",
                error_message="No visible Sonos speakers found.",
            )

        if len(available_speakers) == 1:
            return SonosSelectionPlan(
                status="resolved",
                selected_uids=[available_speakers[0].uid],
                coordinator_uid=available_speakers[0].uid,
            )

        return SonosSelectionPlan(status="needs_choice", speakers=available_speakers)


class SaveSonosSelection:
    def __init__(self, selected_group_repository: SelectedSonosGroupRepository, sonos_service: SonosService):
        self.selected_group_repository = selected_group_repository
        self.sonos_service = sonos_service

    def execute(self, uids: list[str], coordinator_uid: Optional[str] = None) -> SonosSelectionResult:
        available_speakers = self.sonos_service.list_available_speakers()
        validated_group = _validate_selection_request(
            available_speakers=available_speakers,
            requested_uids=uids,
            coordinator_uid=coordinator_uid,
        )
        speakers_by_uid = {speaker.uid: speaker for speaker in available_speakers}
        selected_group = SelectedSonosGroupSettings(
            coordinator_uid=validated_group.coordinator_uid,
            members=[SelectedSonosSpeakerSettings(uid=uid) for uid in validated_group.selected_uids],
        )
        members = [speakers_by_uid[uid] for uid in validated_group.selected_uids]
        coordinator = speakers_by_uid[validated_group.coordinator_uid]
        settings_result = self.selected_group_repository.save_selected_group(selected_group)
        return SonosSelectionResult(
            coordinator=coordinator,
            members=members,
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
                availability=SonosSelectionAvailability(status="not_selected"),
            )

        available_speakers = {speaker.uid: speaker for speaker in self.sonos_service.list_available_speakers()}
        members = []
        coordinator_available = False
        available_member_count = 0

        for saved_member in selected_group.members:
            speaker = available_speakers.get(saved_member.uid)
            if speaker is None:
                members.append(
                    SonosSelectionMemberAvailability(
                        uid=saved_member.uid,
                        status="unavailable",
                    )
                )
                continue

            available_member_count += 1
            if saved_member.uid == selected_group.coordinator_uid:
                coordinator_available = True
            members.append(
                SonosSelectionMemberAvailability(
                    uid=saved_member.uid,
                    status="available",
                    speaker=speaker,
                )
            )

        if not coordinator_available:
            availability = SonosSelectionAvailability(status="unavailable", members=members)
        elif available_member_count == len(selected_group.members):
            availability = SonosSelectionAvailability(status="available", members=members)
        else:
            availability = SonosSelectionAvailability(status="partial", members=members)

        return SonosSelectionStatus(
            selected_group=selected_group,
            availability=availability,
        )


class _ValidatedSonosSelectionRequest(StrictModel):
    selected_uids: list[str]
    coordinator_uid: str


def _validate_selection_request(
    available_speakers: list[DiscoveredSonosSpeaker],
    requested_uids: list[str],
    coordinator_uid: Optional[str] = None,
) -> _ValidatedSonosSelectionRequest:
    if not requested_uids:
        raise ValueError("`uids` must include at least one UID.")

    if len(set(requested_uids)) != len(requested_uids):
        raise ValueError("`uids` must not contain duplicate UIDs.")

    speakers_by_uid = {speaker.uid: speaker for speaker in available_speakers}
    unknown_uids = [uid for uid in requested_uids if uid not in speakers_by_uid]
    if unknown_uids:
        raise ValueError("Selected Sonos speakers are not currently discoverable: {}".format(", ".join(unknown_uids)))

    resolved_coordinator_uid = requested_uids[0] if coordinator_uid is None else coordinator_uid
    if resolved_coordinator_uid not in requested_uids:
        raise ValueError(
            "Selected Sonos coordinator must be one of the selected speakers: {}".format(resolved_coordinator_uid)
        )

    household_ids = {speakers_by_uid[uid].household_id for uid in requested_uids}
    if len(household_ids) != 1:
        raise ValueError("Selected Sonos speakers must belong to the same household.")

    return _ValidatedSonosSelectionRequest(
        selected_uids=list(requested_uids),
        coordinator_uid=resolved_coordinator_uid,
    )
