import socket
from types import ModuleType

import pytest

from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter
from jukebox.sonos.discovery import SonosDiscoveryError, SonosDiscoveryRequest


class FakeSpeaker:
    def __init__(self, uid, name, host, household_id, is_visible=True):
        self.uid = uid
        self.player_name = name
        self.ip_address = host
        self.household_id = household_id
        self.is_visible = is_visible
        self.all_zones = {self}

    def __hash__(self):
        return hash((self.uid, self.ip_address))


def build_fake_soco_module(discover, soco_constructor=None):
    fake_soco = ModuleType("soco")
    setattr(fake_soco, "discover", discover)
    setattr(fake_soco, "SoCo", soco_constructor or (lambda host: None))

    fake_exceptions = ModuleType("soco.exceptions")

    class FakeSoCoException(Exception):
        pass

    class FakeSoCoUPnPException(FakeSoCoException):
        pass

    setattr(fake_exceptions, "SoCoException", FakeSoCoException)
    setattr(fake_exceptions, "SoCoUPnPException", FakeSoCoUPnPException)
    return {"soco": fake_soco, "soco.exceptions": fake_exceptions}


def test_soco_sonos_discovery_adapter_normalizes_and_sorts_speakers(mocker):
    kitchen = FakeSpeaker("speaker-2", "Kitchen", "192.168.1.40", "household-1")
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.30", "household-1")
    office = FakeSpeaker("speaker-3", "Kitchen", "192.168.1.35", "household-1")
    kitchen.all_zones = {kitchen, living_room, office}
    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {kitchen}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [(speaker.name, speaker.host, speaker.uid) for speaker in speakers] == [
        ("Kitchen", "192.168.1.35", "speaker-3"),
        ("Kitchen", "192.168.1.40", "speaker-2"),
        ("Living Room", "192.168.1.30", "speaker-1"),
    ]


def test_soco_sonos_discovery_adapter_deduplicates_by_uid(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen_duplicate = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen.all_zones = {kitchen, kitchen_duplicate}
    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {kitchen}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert len(speakers) == 1
    assert speakers[0].uid == "speaker-1"


def test_soco_sonos_discovery_adapter_preserves_visibility_flag(mocker):
    hidden = FakeSpeaker("speaker-hidden", "Living Room Surround", "192.168.1.99", "household-1", is_visible=False)
    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {hidden}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert len(speakers) == 1
    assert speakers[0].is_visible is False


def test_soco_sonos_discovery_adapter_returns_empty_list_when_no_speakers_are_found(mocker):
    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: set()))
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_responder_hosts", return_value=set())

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert speakers == []


def test_soco_sonos_discovery_adapter_skips_responder_scan_on_normal_fast_path(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {kitchen}))
    discover_responder_hosts = mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_responder_hosts",
        return_value={"192.168.1.99"},
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]
    discover_responder_hosts.assert_not_called()


def test_soco_sonos_discovery_adapter_aggregates_multiple_households_from_responder_hosts(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    living_room = FakeSpeaker("speaker-2", "Living Room", "192.168.1.31", "household-1")
    bar = FakeSpeaker("speaker-3", "Bar", "192.168.1.20", "household-2")
    kitchen.all_zones = {kitchen, living_room}
    bar.all_zones = {bar}
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {kitchen},
            soco_constructor=lambda host: {
                "192.168.1.20": bar,
                "192.168.1.30": kitchen,
            }[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_responder_hosts",
        return_value={"192.168.1.20", "192.168.1.30"},
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers(SonosDiscoveryRequest.all_households())

    assert [(speaker.name, speaker.household_id) for speaker in speakers] == [
        ("Bar", "household-2"),
        ("Kitchen", "household-1"),
        ("Living Room", "household-1"),
    ]


def test_soco_sonos_discovery_adapter_filters_to_target_household(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    bar = FakeSpeaker("speaker-3", "Bar", "192.168.1.20", "household-2")
    bar.all_zones = {bar}

    def discover(*args, **kwargs):
        assert kwargs == {"household_id": "household-2"}
        return set()

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=discover,
            soco_constructor=lambda host: {
                "192.168.1.20": bar,
                "192.168.1.30": kitchen,
            }[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_responder_hosts",
        return_value={"192.168.1.20", "192.168.1.30"},
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers(SonosDiscoveryRequest.target_household("household-2"))

    assert [(speaker.uid, speaker.household_id) for speaker in speakers] == [("speaker-3", "household-2")]


def test_soco_sonos_discovery_adapter_uses_responder_hosts_when_soco_discover_returns_empty(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    living_room.all_zones = {living_room}
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: set(),
            soco_constructor=lambda host: {"192.168.1.20": living_room}[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_responder_hosts",
        return_value={"192.168.1.20"},
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.model_dump() for speaker in speakers] == [
        {
            "uid": "speaker-1",
            "name": "Living Room",
            "host": "192.168.1.20",
            "household_id": "household-1",
            "is_visible": True,
        }
    ]


def test_soco_sonos_discovery_adapter_ignores_unusable_interfaces_during_responder_discovery(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    living_room.all_zones = {living_room}
    fake_modules = build_fake_soco_module(
        discover=lambda: set(),
        soco_constructor=lambda host: {"192.168.1.20": living_room}[host],
    )
    fake_soco_discovery = ModuleType("soco.discovery")
    setattr(fake_soco_discovery, "_find_ipv4_addresses", lambda: ["10.0.0.5", "192.168.1.2"])
    setattr(fake_modules["soco"], "discovery", fake_soco_discovery)
    fake_modules["soco.discovery"] = fake_soco_discovery
    mocker.patch.dict("sys.modules", fake_modules)

    class FakeSocket:
        def __init__(self):
            self.closed = False

        def setsockopt(self, level, option, value):
            if option == socket.IP_MULTICAST_IF and value == b"10.0.0.5":
                raise OSError("bad interface")

        def sendto(self, payload, destination):
            return None

        def recvfrom(self, bufsize):
            return (b"HTTP/1.1 200 OK\r\nSERVER: Linux UPnP/1.0 Sonos/80.0-00000\r\n", ("192.168.1.20", 1900))

        def close(self):
            self.closed = True

    def fake_socket(_family, _type, _proto):
        sock = FakeSocket()
        created_sockets.append(sock)
        return sock

    created_sockets = []

    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter.socket.inet_aton",
        side_effect=lambda address: address.encode(),
    )
    mocker.patch("jukebox.adapters.outbound.sonos_discovery_adapter.socket.socket", side_effect=fake_socket)
    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter.select.select",
        side_effect=lambda sockets, _write, _err, _timeout: ([sockets[0]], [], []),
    )
    mocker.patch("jukebox.adapters.outbound.sonos_discovery_adapter.time.time", side_effect=[0.0, 0.0, 0.0, 1.1])

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.model_dump() for speaker in speakers] == [
        {
            "uid": "speaker-1",
            "name": "Living Room",
            "host": "192.168.1.20",
            "household_id": "household-1",
            "is_visible": True,
        }
    ]
    assert created_sockets[0].closed is True


def test_soco_sonos_discovery_adapter_ignores_stale_discovered_zones(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    class StaleSpeaker:
        all_zones = set()

        @property
        def uid(self):
            raise OSError("stale zone")

        def __hash__(self):
            return hash("stale")

    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {living_room, StaleSpeaker()}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]


def test_soco_sonos_discovery_adapter_recovers_stale_discovered_speaker_by_host(mocker):
    class StaleDiscoveredSpeaker:
        ip_address = "192.168.1.20"
        household_id = "household-1"
        is_visible = True

        def __init__(self):
            self.all_zones = {self}

        @property
        def uid(self):
            return "speaker-1"

        @property
        def player_name(self):
            raise OSError("stale topology")

        def __hash__(self):
            return hash((self.uid, self.ip_address))

    healthy_speaker = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {StaleDiscoveredSpeaker()},
            soco_constructor=lambda host: {"192.168.1.20": healthy_speaker}[host],
        ),
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.model_dump() for speaker in speakers] == [
        {
            "uid": "speaker-1",
            "name": "Living Room",
            "host": "192.168.1.20",
            "household_id": "household-1",
            "is_visible": True,
        }
    ]


def test_soco_sonos_discovery_adapter_ignores_mismatched_host_retry_results(mocker):
    healthy_speaker = FakeSpeaker("speaker-3", "Office", "192.168.1.30", "household-1")

    class StaleDiscoveredSpeaker:
        ip_address = "192.168.1.20"
        household_id = "household-1"
        is_visible = True

        def __init__(self):
            self.all_zones = {self}

        @property
        def uid(self):
            return "speaker-1"

        @property
        def player_name(self):
            raise OSError("stale topology")

        def __hash__(self):
            return hash((self.uid, self.ip_address))

    mismatched_speaker = FakeSpeaker("speaker-2", "Kitchen", "192.168.1.20", "household-1")
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            discover=lambda: {healthy_speaker, StaleDiscoveredSpeaker()},
            soco_constructor=lambda host: {"192.168.1.20": mismatched_speaker}[host],
        ),
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-3"]


def test_soco_sonos_discovery_adapter_raises_when_all_discovered_speakers_fail_normalization(mocker):
    class UnreachableSpeaker:
        ip_address = "10.1.10.87"
        all_zones = set()

        @property
        def uid(self):
            raise OSError("No route to host")

        def __hash__(self):
            return hash("unreachable")

    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {UnreachableSpeaker()}))

    with pytest.raises(
        SonosDiscoveryError,
        match="Discovered Sonos speakers but failed to inspect any reachable speakers: 10.1.10.87: No route to host",
    ):
        SoCoSonosDiscoveryAdapter().discover_speakers()


def test_soco_sonos_discovery_adapter_keeps_reachable_speakers_when_some_fail_normalization(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    class UnreachableSpeaker:
        ip_address = "10.1.10.87"
        all_zones = set()

        @property
        def uid(self):
            raise OSError("No route to host")

        def __hash__(self):
            return hash("unreachable")

    mocker.patch.dict("sys.modules", build_fake_soco_module(discover=lambda: {living_room, UnreachableSpeaker()}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]


def test_soco_sonos_discovery_adapter_wraps_discovery_errors(mocker):
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(discover=lambda: (_ for _ in ()).throw(OSError("network unavailable"))),
    )

    with pytest.raises(SonosDiscoveryError, match="Failed to discover Sonos speakers: network unavailable"):
        SoCoSonosDiscoveryAdapter().discover_speakers()
