from types import ModuleType

import pytest

from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter
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


def build_fake_soco_module(scan_network, soco_constructor=None, discover=None):
    fake_soco = ModuleType("soco")
    setattr(fake_soco, "SoCo", soco_constructor or (lambda host: None))

    fake_discovery = ModuleType("soco.discovery")
    setattr(fake_discovery, "scan_network", scan_network)
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
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: {kitchen}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [(speaker.name, speaker.host, speaker.uid) for speaker in speakers] == [
        ("Kitchen", "192.168.1.35", "speaker-3"),
        ("Kitchen", "192.168.1.40", "speaker-2"),
        ("Living Room", "192.168.1.30", "speaker-1"),
    ]


def test_soco_sonos_discovery_adapter_uses_exhaustive_multi_household_network_scan(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    bar = FakeSpeaker("speaker-2", "Bar", "192.168.1.20", "household-2")
    scan_network = mocker.Mock(return_value={kitchen, bar})
    discover = mocker.Mock()
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=scan_network, discover=discover),
    )

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-2", "speaker-1"]
    scan_network.assert_called_once_with(
        include_invisible=True,
        multi_household=True,
        min_netmask=0,
    )
    discover.assert_not_called()


def test_soco_sonos_discovery_adapter_returns_empty_list_when_no_speakers_are_found(mocker):
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: set()))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert speakers == []


def test_soco_sonos_discovery_adapter_preserves_visibility_flag(mocker):
    hidden = FakeSpeaker("speaker-hidden", "Living Room Surround", "192.168.1.99", "household-1", is_visible=False)
    mocker.patch.dict("sys.modules", build_fake_soco_module(scan_network=lambda **kwargs: {hidden}))

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert len(speakers) == 1
    assert speakers[0].is_visible is False


def test_soco_sonos_discovery_adapter_deduplicates_by_uid(mocker):
    kitchen = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen_duplicate = FakeSpeaker("speaker-1", "Kitchen", "192.168.1.30", "household-1")
    kitchen.all_zones = {kitchen, kitchen_duplicate}
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

    speakers = SoCoSonosDiscoveryAdapter().discover_speakers()

    assert [speaker.uid for speaker in speakers] == ["speaker-1"]


def test_soco_sonos_discovery_adapter_wraps_discovery_errors(mocker):
    mocker.patch.dict(
        "sys.modules",
        build_fake_soco_module(scan_network=lambda **kwargs: (_ for _ in ()).throw(OSError("network unavailable"))),
    )

    with pytest.raises(SonosDiscoveryError, match="Failed to discover Sonos speakers: network unavailable"):
        SoCoSonosDiscoveryAdapter().discover_speakers()
