import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.service import DefaultSonosService


class StubDiscovery:
    def __init__(self, speakers):
        self.speakers = speakers

    def discover_speakers(self):
        return list(self.speakers)


def build_discovered_speaker(uid, name, host, household_id):
    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def test_default_sonos_service_resolves_multi_member_group_from_uids():
    service = DefaultSonosService(
        StubDiscovery(
            [
                build_discovered_speaker("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
                build_discovered_speaker("speaker-2", "Living Room", "192.168.1.40", "household-1"),
            ]
        )
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    resolved_group = service.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-2"
    assert resolved_group.coordinator.host == "192.168.1.40"
    assert [member.uid for member in resolved_group.members] == ["speaker-1", "speaker-2"]
    assert resolved_group.missing_member_uids == []


def test_default_sonos_service_marks_unreachable_non_coordinator_missing():
    service = DefaultSonosService(
        StubDiscovery([build_discovered_speaker("speaker-1", "Living Room", "192.168.1.20", "household-1")])
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    resolved_group = service.resolve_selected_group(selected_group)

    assert [member.uid for member in resolved_group.members] == ["speaker-1"]
    assert resolved_group.missing_member_uids == ["speaker-2"]


def test_default_sonos_service_rejects_unreachable_coordinator():
    service = DefaultSonosService(
        StubDiscovery([build_discovered_speaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")])
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    with pytest.raises(ValueError, match="Unable to resolve saved Sonos coordinator: speaker-2: not found on network"):
        service.resolve_selected_group(selected_group)


def test_default_sonos_service_rejects_members_from_different_households():
    service = DefaultSonosService(
        StubDiscovery(
            [
                build_discovered_speaker("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
                build_discovered_speaker("speaker-2", "Living Room", "192.168.1.40", "household-2"),
            ]
        )
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    with pytest.raises(ValueError, match="same household"):
        service.resolve_selected_group(selected_group)


def test_default_sonos_service_rejects_missing_coordinator_when_discovery_is_empty():
    service = DefaultSonosService(StubDiscovery([]))
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    with pytest.raises(ValueError, match="speaker-1: not found on network"):
        service.resolve_selected_group(selected_group)
