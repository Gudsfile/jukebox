import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoverySnapshot
from jukebox.sonos.service import DefaultSonosService


class StubDiscovery:
    def __init__(self, speakers, retry_hosts_by_uid=None, resolved_by_host=None, resolve_errors=None):
        self.speakers = speakers
        self.retry_hosts_by_uid = retry_hosts_by_uid or {}
        self.resolved_by_host = resolved_by_host or {}
        self.resolve_errors = resolve_errors or {}

    def discover_speakers(self):
        return list(self.speakers)

    def discover_runtime_snapshot(self):
        return SonosDiscoverySnapshot(
            speakers=list(self.speakers),
            retry_hosts_by_uid={uid: list(hosts) for uid, hosts in self.retry_hosts_by_uid.items()},
            normalization_errors=[],
        )

    def resolve_speaker_by_host(self, expected_uid, host):
        error = self.resolve_errors.get((expected_uid, host))
        if error is not None:
            raise error
        return self.resolved_by_host[(expected_uid, host)]


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


def test_default_sonos_service_retries_stale_discovered_member_by_saved_uid():
    service = DefaultSonosService(
        StubDiscovery(
            [],
            retry_hosts_by_uid={"speaker-1": ["192.168.1.20"]},
            resolved_by_host={
                ("speaker-1", "192.168.1.20"): build_discovered_speaker(
                    "speaker-1",
                    "Living Room",
                    "192.168.1.20",
                    "household-1",
                )
            },
        )
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    resolved_group = service.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-1"
    assert resolved_group.coordinator.host == "192.168.1.20"


def test_default_sonos_service_marks_non_coordinator_missing_when_host_retry_fails():
    service = DefaultSonosService(
        StubDiscovery(
            [build_discovered_speaker("speaker-1", "Living Room", "192.168.1.20", "household-1")],
            retry_hosts_by_uid={"speaker-2": ["192.168.1.30"]},
            resolve_errors={
                ("speaker-2", "192.168.1.30"): ValueError(
                    "Failed to contact saved Sonos speaker at 192.168.1.30: timed out"
                )
            },
        )
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


def test_default_sonos_service_rejects_coordinator_when_host_retry_fails():
    service = DefaultSonosService(
        StubDiscovery(
            [],
            retry_hosts_by_uid={"speaker-1": ["192.168.1.20"]},
            resolve_errors={
                ("speaker-1", "192.168.1.20"): ValueError(
                    "Saved Sonos speaker UID mismatch for host 192.168.1.20: expected speaker-1, resolved speaker-9"
                )
            },
        )
    )
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    with pytest.raises(
        ValueError,
        match="speaker-1 via 192.168.1.20: Saved Sonos speaker UID mismatch",
    ):
        service.resolve_selected_group(selected_group)
