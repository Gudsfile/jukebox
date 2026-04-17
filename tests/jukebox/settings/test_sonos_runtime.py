import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.service import DefaultSonosService


class StubDiscovery:
    def __init__(self, network_speakers):
        self.network_speakers = network_speakers
        self.requests = []

    def discover_speakers(self):
        self.requests.append(("network", None))
        return list(self.network_speakers)


def build_discovered_speaker(uid, name, host, household_id):
    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def test_default_sonos_service_resolves_multi_member_group_from_uids():
    discovery = StubDiscovery(
        [
            build_discovered_speaker("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            build_discovered_speaker("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ]
    )
    service = DefaultSonosService(discovery)
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
    assert discovery.requests == [("network", None)]


def test_default_sonos_service_lists_network_speakers():
    discovery = StubDiscovery(
        [
            build_discovered_speaker("speaker-1", "Kitchen", "192.168.1.30", "household-2"),
            build_discovered_speaker("speaker-2", "Living Room", "192.168.1.40", "household-2"),
            build_discovered_speaker("speaker-3", "Bar", "192.168.1.20", "household-1"),
        ]
    )
    service = DefaultSonosService(discovery)

    speakers = service.list_network_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-3", "speaker-1", "speaker-2"]
    assert discovery.requests == [("network", None)]


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


def test_default_sonos_service_inspect_selected_group_matches_runtime_for_mixed_households():
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

    inspection = service.inspect_selected_group(selected_group)

    assert inspection.error_message == "Resolved Sonos group members must belong to the same household"

    with pytest.raises(ValueError, match="same household"):
        service.resolve_selected_group(selected_group)


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
