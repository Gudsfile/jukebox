from types import ModuleType

import ifaddr
import pytest

from jukebox.adapters.outbound.sonos_discovery_adapter import (
    SoCoSonosDiscoveryAdapter,
    _build_private_ipv4_networks_to_scan,
    _extract_sonos_household_id,
)
from jukebox.sonos.discovery import SonosDiscoveryError


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


def build_fake_soco_module(scan_network, soco_constructor=None, discover=None, find_ipv4_addresses=None):
    fake_soco = ModuleType("soco")
    setattr(fake_soco, "SoCo", soco_constructor or (lambda host: None))

    fake_discovery = ModuleType("soco.discovery")
    setattr(fake_discovery, "scan_network", scan_network)
    setattr(fake_discovery, "_find_ipv4_addresses", find_ipv4_addresses or (lambda: {"192.168.1.10"}))
    setattr(
        fake_discovery,
        "discover",
        discover or (lambda **kwargs: (_ for _ in ()).throw(AssertionError("discover should not be called"))),
    )
    setattr(fake_soco, "discovery", fake_discovery)
    setattr(
        fake_soco,
        "discover",
        discover or (lambda **kwargs: (_ for _ in ()).throw(AssertionError("discover should not be called"))),
    )

    fake_exceptions = ModuleType("soco.exceptions")

    class FakeSoCoException(Exception):
        pass

    class FakeSoCoUPnPException(FakeSoCoException):
        pass

    setattr(fake_exceptions, "SoCoException", FakeSoCoException)
    setattr(fake_exceptions, "SoCoUPnPException", FakeSoCoUPnPException)
    return {
        "soco": fake_soco,
        "soco.discovery": fake_discovery,
        "soco.exceptions": fake_exceptions,
    }


def test_soco_sonos_discovery_adapter_normalizes_and_sorts_speakers(mocker):
    kitchen = FakeSpeaker("speaker-2", "Kitchen", "192.168.1.40", "household-1")
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.30", "household-1")
    office = FakeSpeaker("speaker-3", "Kitchen", "192.168.1.35", "household-1")
    kitchen.all_zones = {kitchen, living_room, office}
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value={kitchen})
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: {kitchen}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [(speaker.name, speaker.host, speaker.uid) for speaker in speakers] == [
        ("Kitchen", "192.168.1.35", "speaker-3"),
        ("Kitchen", "192.168.1.40", "speaker-2"),
        ("Living Room", "192.168.1.30", "speaker-1"),
    ]


def test_soco_sonos_discovery_adapter_uses_multicast_discovery_before_scan_fallback(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    bar = FakeSpeaker("speaker-2", "Bar", "192.168.1.20", "household-2")
    multicast_discovery = mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={kitchen, bar},
    )
    scan_network = mocker.Mock(return_value={kitchen, bar})
    discover = mocker.Mock()
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=scan_network, discover=discover),
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-2", "speaker-1"]
    multicast_discovery.assert_called_once_with()
    scan_network.assert_not_called()
    discover.assert_not_called()


def test_soco_sonos_discovery_adapter_falls_back_to_bounded_network_scan(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value=set())
    scan_network = mocker.Mock(return_value={kitchen})
    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter._build_private_ipv4_networks_to_scan",
        return_value=["192.168.4.0/22", "192.168.64.0/24"],
    )
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=scan_network))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]
    scan_network.assert_called_once_with(
        include_invisible=True,
        multi_household=True,
        networks_to_scan=["192.168.4.0/22", "192.168.64.0/24"],
    )


def test_soco_sonos_discovery_adapter_keeps_healthy_households_when_one_multicast_seed_fails(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")

    class UnreachableZone:
        @property
        def all_zones(self):
            raise OSError("stale seed")

    scan_network = mocker.Mock(return_value={FakeSpeaker("speaker-9", "Fallback", "192.168.1.90", "household-9")})
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            scan_network=scan_network,
            soco_constructor=lambda host: {
                "192.168.1.30": kitchen,
                "192.168.1.40": UnreachableZone(),
            }[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_collect_multicast_household_hosts",
        return_value={"household-1": ["192.168.1.30"], "household-2": ["192.168.1.40"]},
    )
    mock_socket = mocker.Mock()
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_create_multicast_socket", return_value=mock_socket)

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]
    scan_network.assert_not_called()


def test_soco_sonos_discovery_adapter_falls_back_when_all_multicast_seeds_fail(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")

    class UnreachableZone:
        @property
        def all_zones(self):
            raise OSError("stale seed")

    scan_network = mocker.Mock(return_value={kitchen})
    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter._build_private_ipv4_networks_to_scan",
        return_value=["192.168.4.0/22"],
    )
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            scan_network=scan_network,
            soco_constructor=lambda host: UnreachableZone(),
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_collect_multicast_household_hosts",
        return_value={"household-1": ["192.168.1.30"]},
    )
    mock_socket = mocker.Mock()
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_create_multicast_socket", return_value=mock_socket)

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]
    scan_network.assert_called_once_with(
        include_invisible=True,
        multi_household=True,
        networks_to_scan=["192.168.4.0/22"],
    )


def test_soco_sonos_discovery_adapter_retries_second_multicast_seed_in_same_household(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")

    class UnreachableZone:
        @property
        def all_zones(self):
            raise OSError("stale seed")

    scan_network = mocker.Mock(return_value={FakeSpeaker("speaker-9", "Fallback", "192.168.1.90", "household-9")})
    soco_constructor = mocker.Mock(
        side_effect=lambda host: {
            "192.168.1.20": UnreachableZone(),
            "192.168.1.30": kitchen,
        }[host]
    )
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            scan_network=scan_network,
            soco_constructor=soco_constructor,
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_collect_multicast_household_hosts",
        return_value={"household-1": ["192.168.1.20", "192.168.1.30"]},
    )
    mock_socket = mocker.Mock()
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_create_multicast_socket", return_value=mock_socket)

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]
    assert soco_constructor.call_args_list[0].args == ("192.168.1.20",)
    assert soco_constructor.call_args_list[1].args == ("192.168.1.30",)
    scan_network.assert_not_called()


def test_soco_sonos_discovery_adapter_returns_empty_list_when_no_speakers_are_found(mocker):
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value=set())
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: set()))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert speakers == []


def test_soco_sonos_discovery_adapter_preserves_visibility_flag(mocker):
    hidden = FakeSpeaker("speaker-hidden", "Living Room Surround", "192.168.1.99", "household-1", is_visible=False)
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value={hidden})
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: {hidden}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert len(speakers) == 1
    assert speakers[0].is_visible is False


def test_soco_sonos_discovery_adapter_deduplicates_by_uid(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen_duplicate = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen.all_zones = {kitchen, kitchen_duplicate}
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value={kitchen})
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: {kitchen}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert len(speakers) == 1
    assert speakers[0].uid == "speaker-1"


def test_soco_sonos_discovery_adapter_ignores_stale_discovered_zones(mocker):
    living_room = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", "household-1")

    class StaleSpeaker:
        all_zones = set()

        @property
        def uid(self):
            raise OSError("stale zone")

        def __hash__(self):
            return hash("stale")

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=lambda **kwargs: {living_room, StaleSpeaker()}),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={living_room, StaleSpeaker()},
    )

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
            scan_network=lambda **kwargs: {StaleDiscoveredSpeaker()},
            soco_constructor=lambda host: {"192.168.1.20": healthy_speaker}[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={StaleDiscoveredSpeaker()},
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


def test_soco_sonos_discovery_adapter_recovers_stale_household_speaker_by_host(mocker):
    household_id = "household-1"

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

    healthy_speaker = FakeSpeaker("speaker-1", "Living Room", "192.168.1.20", household_id)
    discover = mocker.Mock(return_value={StaleDiscoveredSpeaker()})
    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter._build_private_ipv4_networks_to_scan",
        return_value=["192.168.4.0/22"],
    )
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(
            scan_network=lambda **kwargs: set(),
            discover=discover,
            soco_constructor=lambda host: {"192.168.1.20": healthy_speaker}[host],
        ),
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_household_speakers(household_id)

    assert [speaker.model_dump() for speaker in speakers] == [
        {
            "uid": "speaker-1",
            "name": "Living Room",
            "host": "192.168.1.20",
            "household_id": household_id,
            "is_visible": True,
        }
    ]
    discover.assert_called_once_with(
        include_invisible=True,
        household_id=household_id,
        allow_network_scan=True,
        networks_to_scan=["192.168.4.0/22"],
    )


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
            scan_network=lambda **kwargs: {healthy_speaker, StaleDiscoveredSpeaker()},
            soco_constructor=lambda host: {"192.168.1.20": mismatched_speaker}[host],
        ),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={healthy_speaker, StaleDiscoveredSpeaker()},
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

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=lambda **kwargs: {UnreachableSpeaker()}),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={UnreachableSpeaker()},
    )

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

    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=lambda **kwargs: {living_room, UnreachableSpeaker()}),
    )
    mocker.patch.object(
        SoCoSonosDiscoveryAdapter,
        "_discover_multicast_network_speakers",
        return_value={living_room, UnreachableSpeaker()},
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]


def test_soco_sonos_discovery_adapter_wraps_discovery_errors(mocker):
    mocker.patch.object(SoCoSonosDiscoveryAdapter, "_discover_multicast_network_speakers", return_value=set())
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=lambda **kwargs: (_ for _ in ()).throw(OSError("network unavailable"))),
    )

    with pytest.raises(SonosDiscoveryError, match="Failed to discover Sonos speakers: network unavailable"):
        SoCoSonosDiscoveryAdapter().discover_speakers()


def test_extract_sonos_household_id_returns_none_without_header():
    assert _extract_sonos_household_id(b"HTTP/1.1 200 OK\r\nSERVER: Sonos\r\n\r\n") is None


def test_build_private_ipv4_networks_to_scan_filters_to_private_ipv4_subnets(mocker):
    adapters = [
        ifaddr._shared.Adapter(
            "corp0",
            "corp0",
            [ifaddr.IP("10.12.34.56", 16, "corp0")],
            index=0,
        ),
        ifaddr._shared.Adapter(
            "en0",
            "en0",
            [
                ifaddr.IP("192.168.4.68", 22, "en0"),
                ifaddr.IP("fe80::1", 64, "en0"),
            ],
            index=1,
        ),
        ifaddr._shared.Adapter(
            "bridge100",
            "bridge100",
            [ifaddr.IP("192.168.64.1", 24, "bridge100")],
            index=2,
        ),
        ifaddr._shared.Adapter(
            "lo0",
            "lo0",
            [ifaddr.IP("127.0.0.1", 8, "lo0")],
            index=3,
        ),
        ifaddr._shared.Adapter(
            "utun9",
            "utun9",
            [ifaddr.IP("100.90.85.13", 32, "utun9")],
            index=4,
        ),
    ]
    mocker.patch("ifaddr.get_adapters", return_value=adapters)

    assert _build_private_ipv4_networks_to_scan() == [
        "10.12.32.0/22",
        "192.168.4.0/22",
        "192.168.64.0/24",
    ]


def test_collect_multicast_household_hosts_tracks_all_seed_hosts_per_household(mocker):
    socket_one = mocker.Mock()
    socket_two = mocker.Mock()
    socket_one.recvfrom.side_effect = [
        (
            b"HTTP/1.1 200 OK\r\nX-RINCON-HOUSEHOLD: Sonos_A\r\n\r\n",
            ("192.168.1.20", 1900),
        ),
        (
            b"HTTP/1.1 200 OK\r\nX-RINCON-HOUSEHOLD: Sonos_A\r\n\r\n",
            ("192.168.1.21", 1900),
        ),
    ]
    socket_two.recvfrom.return_value = (
        b"HTTP/1.1 200 OK\r\nX-RINCON-HOUSEHOLD: Sonos_B\r\n\r\n",
        ("192.168.1.30", 1900),
    )
    select_mock = mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter.select.select",
        side_effect=[
            ([socket_one, socket_two], [], []),
            ([socket_one], [], []),
            ([], [], []),
        ],
    )
    mocker.patch(
        "jukebox.adapters.outbound.sonos_discovery_adapter.time.monotonic",
        side_effect=[0.0, 0.2, 0.4, 1.2],
    )

    household_hosts = SoCoSonosDiscoveryAdapter()._collect_multicast_household_hosts([socket_one, socket_two])

    assert household_hosts == {
        "Sonos_A": ["192.168.1.20", "192.168.1.21"],
        "Sonos_B": ["192.168.1.30"],
    }
    assert select_mock.call_count == 2
