from typing import Protocol

from jukebox.settings.entities import (
    ResolvedSonosGroupRuntime,
    ResolvedSonosSpeakerRuntime,
    SelectedSonosGroupSettings,
)

from .discovery import DiscoveredSonosSpeaker, SonosDiscoveryPort, sort_sonos_speakers


class SonosService(Protocol):
    def list_available_speakers(self) -> list[DiscoveredSonosSpeaker]: ...

    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime: ...


class DefaultSonosService:
    def __init__(self, discovery: SonosDiscoveryPort):
        self.discovery = discovery

    def list_available_speakers(self) -> list[DiscoveredSonosSpeaker]:
        return sort_sonos_speakers([speaker for speaker in self.discovery.discover_speakers() if speaker.is_visible])

    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime:
        available_speakers = {speaker.uid: speaker for speaker in self.discovery.discover_speakers()}
        resolved_members = []
        missing_member_uids = []
        coordinator_resolution_error = None

        for saved_member in selected_group.members:
            resolved_speaker = available_speakers.get(saved_member.uid)
            runtime_member = self._build_runtime_speaker(resolved_speaker) if resolved_speaker is not None else None
            member_resolution_error = (
                None if runtime_member is not None else f"{saved_member.uid}: not found on network"
            )

            if runtime_member is None:
                if saved_member.uid == selected_group.coordinator_uid:
                    coordinator_resolution_error = member_resolution_error
                else:
                    missing_member_uids.append(saved_member.uid)
                continue

            resolved_members.append(runtime_member)

        coordinator = next(
            (member for member in resolved_members if member.uid == selected_group.coordinator_uid),
            None,
        )
        if coordinator is None:
            if coordinator_resolution_error is not None:
                raise ValueError(f"Unable to resolve saved Sonos coordinator: {coordinator_resolution_error}")
            raise ValueError("Saved Sonos coordinator did not resolve to one of the selected_group members")

        household_ids = {member.household_id for member in resolved_members}
        if len(household_ids) != 1:
            raise ValueError("Resolved Sonos group members must belong to the same household")

        return ResolvedSonosGroupRuntime(
            household_id=coordinator.household_id,
            coordinator=coordinator,
            members=resolved_members,
            missing_member_uids=missing_member_uids,
        )

    @staticmethod
    def _build_runtime_speaker(speaker: DiscoveredSonosSpeaker) -> ResolvedSonosSpeakerRuntime:
        return ResolvedSonosSpeakerRuntime(
            uid=speaker.uid,
            name=speaker.name,
            host=speaker.host,
            household_id=speaker.household_id,
        )
