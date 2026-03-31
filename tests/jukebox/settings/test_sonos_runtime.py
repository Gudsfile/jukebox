from types import ModuleType

import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.settings.sonos_runtime import SoCoSonosGroupResolver


class FakeSpeaker:
    def __init__(self, uid, name, host, household_id):
        self.uid = uid
        self.player_name = name
        self.ip_address = host
        self.household_id = household_id
        self.all_zones = {self}

    def __hash__(self):
        return hash(self.uid)


def build_fake_soco_module(discover, soco_constructor):
    fake_soco = ModuleType("soco")
    setattr(fake_soco, "discover", discover)
    setattr(fake_soco, "SoCo", soco_constructor)

    fake_exceptions = ModuleType("soco.exceptions")

    class FakeSoCoException(Exception):
        pass

    class FakeSoCoUPnPException(FakeSoCoException):
        pass

    setattr(fake_exceptions, "SoCoException", FakeSoCoException)
    setattr(fake_exceptions, "SoCoUPnPException", FakeSoCoUPnPException)
    return {"soco": fake_soco, "soco.exceptions": fake_exceptions}


def test_soco_sonos_group_resolver_resolves_multi_member_group_from_uids(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    living_room = FakeSpeaker("speaker-2", "Living Room", "192.168.1.40", "household-1")
    kitchen.all_zones = {kitchen, living_room}
    living_room.all_zones = {kitchen, living_room}
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {kitchen},
            soco_constructor=lambda host: {"192.168.1.30": kitchen, "192.168.1.40": living_room}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-2"
    assert resolved_group.coordinator.host == "192.168.1.40"
    assert [member.uid for member in resolved_group.members] == ["speaker-1", "speaker-2"]
    assert resolved_group.missing_member_uids == []


def test_soco_sonos_group_resolver_marks_unreachable_non_coordinator_missing(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room},
            soco_constructor=lambda host: living_room,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert [member.uid for member in resolved_group.members] == ["speaker-1"]
    assert resolved_group.missing_member_uids == ["speaker-2"]


def test_soco_sonos_group_resolver_rejects_unreachable_coordinator(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {kitchen},
            soco_constructor=lambda host: kitchen,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    with pytest.raises(ValueError, match="Unable to resolve saved Sonos coordinator|Saved Sonos coordinator"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_rejects_members_from_different_households(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    living_room = FakeSpeaker("speaker-2", "Living Room", "192.168.1.40", "household-2")
    kitchen.all_zones = {kitchen, living_room}
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {kitchen},
            soco_constructor=lambda host: {"192.168.1.30": kitchen, "192.168.1.40": living_room}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    with pytest.raises(ValueError, match="same household"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_wraps_discovery_errors(mocker):
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: (_ for _ in ()).throw(OSError("network unavailable")),
            soco_constructor=lambda host: None,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    with pytest.raises(ValueError, match="Failed to discover Sonos speakers: network unavailable"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_ignores_stale_discovered_zones_for_other_speakers(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    class StaleSpeaker:
        all_zones = set()
        ip_address = "192.168.1.99"

        @property
        def uid(self):
            raise OSError("stale zone")

        def __hash__(self):
            return hash(self.ip_address)

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room, StaleSpeaker()},
            soco_constructor=lambda host: {"192.168.1.20": living_room}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-1"


def test_soco_sonos_group_resolver_retries_stale_discovered_member_via_discovered_ip(mocker):
    class StaleDiscoveredSpeaker:
        def __init__(self, uid, host):
            self._uid = uid
            self.ip_address = host
            self.all_zones = {self}

        @property
        def uid(self):
            return self._uid

        @property
        def player_name(self):
            raise OSError("stale topology")

        @property
        def household_id(self):
            return "household-1"

        def __hash__(self):
            return hash((self._uid, self.ip_address))

    discovered_speaker = StaleDiscoveredSpeaker("speaker-1", "192.168.1.20")
    healthy_speaker = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {discovered_speaker},
            soco_constructor=lambda host: {"192.168.1.20": healthy_speaker}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-1"
    assert resolved_group.coordinator.name == "Living Room"


def test_soco_sonos_group_resolver_marks_non_coordinator_missing_when_discovered_retry_fails(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    class StaleDiscoveredSpeaker:
        def __init__(self, uid, host):
            self._uid = uid
            self.ip_address = host
            self.all_zones = {self}

        @property
        def uid(self):
            return self._uid

        @property
        def player_name(self):
            raise OSError("stale topology")

        @property
        def household_id(self):
            return "household-1"

        def __hash__(self):
            return hash((self._uid, self.ip_address))

    stale_kitchen = StaleDiscoveredSpeaker("speaker-2", "192.168.1.30")

    def raise_timeout(host):
        if host == "192.168.1.30":
            raise TimeoutError("192.168.1.30 timed out")
        return living_room

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room, stale_kitchen},
            soco_constructor=raise_timeout,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert [member.uid for member in resolved_group.members] == ["speaker-1"]
    assert resolved_group.missing_member_uids == ["speaker-2"]


def test_soco_sonos_group_resolver_rejects_missing_coordinator_when_discovery_is_empty(mocker):
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: None,
            soco_constructor=lambda host: None,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    with pytest.raises(ValueError, match="speaker-1: not found on network"):
        resolver.resolve_selected_group(selected_group)
