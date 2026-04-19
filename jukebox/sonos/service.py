from dataclasses import dataclass, field
from typing import Optional, Protocol

from jukebox.settings.entities import (
    ResolvedSonosGroupRuntime,
    ResolvedSonosSpeakerRuntime,
    SelectedSonosGroupSettings,
)

from .discovery import (
    DiscoveredSonosSpeaker,
    SonosDiscoveryPort,
    sort_sonos_speakers,
)


class SonosService(Protocol):
    def list_network_speakers(self) -> list[DiscoveredSonosSpeaker]: ...

    def inspect_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> "InspectedSelectedSonosGroup": ...

    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime: ...


@dataclass(frozen=True)
class InspectedSelectedSonosGroup:
    coordinator: Optional[DiscoveredSonosSpeaker]
    resolved_members: list[DiscoveredSonosSpeaker]
    missing_member_uids: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


class DefaultSonosService:
    def __init__(self, discovery: SonosDiscoveryPort):
        self.discovery = discovery

    def list_network_speakers(self) -> list[DiscoveredSonosSpeaker]:
        return self._filter_visible_speakers(self.discovery.discover_speakers())

    def inspect_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> InspectedSelectedSonosGroup:
        if selected_group.household_id is None:
            return _inspect_selected_group(
                selected_group=selected_group,
                speakers=self.discovery.discover_speakers(),
            )

        household_inspection = _inspect_selected_group(
            selected_group=selected_group,
            speakers=sort_sonos_speakers(self.discovery.discover_household_speakers(selected_group.household_id)),
        )
        if not _inspection_needs_network_fallback(household_inspection, selected_group):
            return household_inspection

        return _inspect_selected_group(
            selected_group=selected_group,
            speakers=self.discovery.discover_speakers(),
        )

    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime:
        inspection = self.inspect_selected_group(selected_group)
        if inspection.error_message is not None:
            raise ValueError(inspection.error_message)

        if inspection.coordinator is None:
            raise ValueError("Saved Sonos coordinator did not resolve to one of the selected_group members")

        coordinator = self._build_runtime_speaker(inspection.coordinator)
        resolved_members = [self._build_runtime_speaker(member) for member in inspection.resolved_members]

        return ResolvedSonosGroupRuntime(
            household_id=coordinator.household_id,
            coordinator=coordinator,
            members=resolved_members,
            missing_member_uids=inspection.missing_member_uids,
        )

    @staticmethod
    def _build_runtime_speaker(speaker: DiscoveredSonosSpeaker) -> ResolvedSonosSpeakerRuntime:
        return ResolvedSonosSpeakerRuntime(
            uid=speaker.uid,
            name=speaker.name,
            host=speaker.host,
            household_id=speaker.household_id,
        )

    @staticmethod
    def _filter_visible_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
        return sort_sonos_speakers([speaker for speaker in speakers if speaker.is_visible])


def _inspect_selected_group(
    selected_group: SelectedSonosGroupSettings,
    speakers: list[DiscoveredSonosSpeaker],
) -> InspectedSelectedSonosGroup:
    available_speakers = {speaker.uid: speaker for speaker in speakers}
    resolved_members = []
    missing_member_uids = []

    for saved_member in selected_group.members:
        resolved_speaker = available_speakers.get(saved_member.uid)

        if resolved_speaker is None:
            if saved_member.uid != selected_group.coordinator_uid:
                missing_member_uids.append(saved_member.uid)
            continue

        resolved_members.append(resolved_speaker)

    coordinator = next(
        (member for member in resolved_members if member.uid == selected_group.coordinator_uid),
        None,
    )
    if coordinator is None:
        return InspectedSelectedSonosGroup(
            coordinator=None,
            resolved_members=resolved_members,
            missing_member_uids=missing_member_uids,
            error_message=f"Unable to resolve saved Sonos coordinator: {selected_group.coordinator_uid}: not found on network",
        )

    household_ids = {member.household_id for member in resolved_members}
    if len(household_ids) != 1:
        return InspectedSelectedSonosGroup(
            coordinator=coordinator,
            resolved_members=resolved_members,
            missing_member_uids=missing_member_uids,
            error_message="Resolved Sonos group members must belong to the same household",
        )

    return InspectedSelectedSonosGroup(
        coordinator=coordinator,
        resolved_members=resolved_members,
        missing_member_uids=missing_member_uids,
    )


def _inspection_needs_network_fallback(
    inspection: InspectedSelectedSonosGroup,
    selected_group: SelectedSonosGroupSettings,
) -> bool:
    if inspection.error_message is not None:
        return True
    return len(inspection.resolved_members) != len(selected_group.members)
