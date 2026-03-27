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
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Kitchen"),
            SelectedSonosSpeakerSettings(uid="speaker-2", name="Living Room"),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-2"
    assert resolved_group.coordinator.host == "192.168.1.40"
    assert [member.uid for member in resolved_group.members] == ["speaker-1", "speaker-2"]


def test_soco_sonos_group_resolver_falls_back_to_last_known_host_for_missing_speaker(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    kitchen = FakeSpeaker("speaker-2", "Kitchen", "192.168.1.30", "household-1")
    living_room.all_zones = {living_room}
    kitchen.all_zones = {living_room, kitchen}
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room},
            soco_constructor=lambda host: {"192.168.1.20": living_room, "192.168.1.30": kitchen}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room"),
            SelectedSonosSpeakerSettings(
                uid="speaker-2",
                name="Kitchen",
                last_known_host="192.168.1.30",
            ),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert [member.uid for member in resolved_group.members] == ["speaker-1", "speaker-2"]


def test_soco_sonos_group_resolver_falls_back_to_last_known_hosts_when_discovery_is_empty(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    kitchen = FakeSpeaker("speaker-2", "Kitchen", "192.168.1.30", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: None,
            soco_constructor=lambda host: {"192.168.1.20": living_room, "192.168.1.30": kitchen}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(
                uid="speaker-1",
                name="Living Room",
                last_known_host="192.168.1.20",
            ),
            SelectedSonosSpeakerSettings(
                uid="speaker-2",
                name="Kitchen",
                last_known_host="192.168.1.30",
            ),
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert [member.uid for member in resolved_group.members] == ["speaker-1", "speaker-2"]


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
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Kitchen"),
            SelectedSonosSpeakerSettings(uid="speaker-2", name="Living Room", last_known_host="192.168.1.40"),
        ],
    )

    with pytest.raises(ValueError, match="same household"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_aggregates_host_fallback_resolution_failures(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    impostor = FakeSpeaker("speaker-wrong", "Impostor", "192.168.1.30", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room},
            soco_constructor=lambda host: {"192.168.1.20": living_room, "192.168.1.30": impostor}[host],
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room"),
            SelectedSonosSpeakerSettings(
                uid="speaker-2",
                name="Kitchen",
                last_known_host="192.168.1.30",
            ),
        ],
    )

    with pytest.raises(ValueError, match="speaker-2 via 192.168.1.30"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_reports_missing_member_without_last_known_host(mocker):
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
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room"),
            SelectedSonosSpeakerSettings(uid="speaker-2", name="Kitchen"),
        ],
    )

    with pytest.raises(ValueError, match="speaker-2: not found on network and has no last_known_host"):
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
        members=[SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room")],
    )

    with pytest.raises(ValueError, match="Failed to discover Sonos speakers: network unavailable"):
        resolver.resolve_selected_group(selected_group)


def test_soco_sonos_group_resolver_wraps_host_contact_errors(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    def raise_timeout(host):
        raise TimeoutError(f"{host} timed out")

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {living_room},
            soco_constructor=raise_timeout,
        ),
    )

    resolver = SoCoSonosGroupResolver()
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room"),
            SelectedSonosSpeakerSettings(
                uid="speaker-2",
                name="Kitchen",
                last_known_host="192.168.1.30",
            ),
        ],
    )

    with pytest.raises(ValueError, match="Failed to contact saved Sonos speaker at 192.168.1.30"):
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
        members=[SelectedSonosSpeakerSettings(uid="speaker-1", name="Living Room")],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.uid == "speaker-1"


def test_soco_sonos_group_resolver_falls_back_to_last_known_host_when_discovered_member_is_stale(mocker):
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
        members=[
            SelectedSonosSpeakerSettings(
                uid="speaker-1",
                name="Living Room",
                last_known_host="192.168.1.20",
            )
        ],
    )

    resolved_group = resolver.resolve_selected_group(selected_group)

    assert resolved_group.coordinator.name == "Living Room"
