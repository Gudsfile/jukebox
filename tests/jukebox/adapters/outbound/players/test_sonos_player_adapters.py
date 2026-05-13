from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestConnectionError
from soco.exceptions import SoCoUPnPException

from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.domain.errors import PlaybackError
from jukebox.settings.errors import InvalidSettingsError
from tests.jukebox.settings._helpers import StubSonosService, build_resolved_sonos_group_runtime


def make_exception(code: str):
    return SoCoUPnPException(f"UPnP Error {code} received", code, f"<errorCode>{code}</errorCode>")


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_host(mock_sharelink, mock_soco):
    SonosPlayerAdapter(host="192.168.1.100")
    mock_soco.assert_called_once_with("192.168.1.100")
    mock_sharelink.assert_called_once_with(mock_soco.return_value)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_without_host_triggers_discovery(mock_sharelink, mock_soco_module):
    """Should use auto-discovery when no host is provided."""
    mock_speaker = MagicMock()
    mock_speaker.player_name = "Living Room"
    mock_soco_module.discover.return_value = {mock_speaker}

    adapter = SonosPlayerAdapter()

    mock_soco_module.discover.assert_called_once()
    mock_sharelink.assert_called_once_with(mock_speaker)
    assert adapter.speaker is mock_speaker


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_without_host_raises_when_no_speakers_found(mock_sharelink, mock_soco_module):
    """Should raise InvalidSettingsError when discovery finds no speakers."""
    mock_soco_module.discover.return_value = None

    with pytest.raises(InvalidSettingsError, match="No Sonos speakers found on the network"):
        SonosPlayerAdapter()

    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_discovery_picks_first_speaker_alphabetically(mock_sharelink, mock_soco_module):
    """Should pick the alphabetically first speaker when multiple are discovered."""
    speaker_b = MagicMock()
    speaker_b.player_name = "Kitchen"
    speaker_a = MagicMock()
    speaker_a.player_name = "Bedroom"

    mock_soco_module.discover.return_value = {speaker_b, speaker_a}

    adapter = SonosPlayerAdapter()

    assert adapter.speaker is speaker_a


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_name_selects_matching_speaker(mock_sharelink, mock_soco_module):
    """Should select the speaker matching the given name."""
    speaker_a = MagicMock()
    speaker_a.player_name = "Kitchen"
    speaker_b = MagicMock()
    speaker_b.player_name = "Living Room"
    mock_soco_module.discover.return_value = {speaker_a, speaker_b}

    adapter = SonosPlayerAdapter(name="Living Room")

    assert adapter.speaker is speaker_b


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_name_raises_when_speaker_not_found(mock_sharelink, mock_soco_module):
    """Should raise InvalidSettingsError when the named speaker is not found."""
    mock_speaker = MagicMock()
    mock_speaker.player_name = "Kitchen"
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_soco_module.discover.return_value = {mock_speaker}

    with pytest.raises(InvalidSettingsError, match="No Sonos speaker named 'Bedroom' found on the network"):
        SonosPlayerAdapter(name="Bedroom")

    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_resolved_group_enforces_membership_before_playback(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    current_group = MagicMock()
    current_group.coordinator = coordinator
    extra = MagicMock()
    extra.uid = "speaker-extra"
    extra.player_name = "Office"
    current_group.members = {coordinator, extra}
    coordinator.group = current_group

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    adapter = SonosPlayerAdapter(group=group)

    kitchen.join.assert_called_once_with(coordinator)
    extra.unjoin.assert_called_once_with()
    mock_sharelink.assert_called_once_with(coordinator)
    assert adapter.speaker is coordinator


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_resolved_group_preserves_nonvisible_members(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}

    invisible_satellite = MagicMock()
    invisible_satellite.uid = "speaker-satellite"
    invisible_satellite.player_name = "Living Room Surround"
    invisible_satellite.is_visible = False

    invisible_stereo_peer = MagicMock()
    invisible_stereo_peer.uid = "speaker-stereo-peer"
    invisible_stereo_peer.player_name = "Living Room Right"
    invisible_stereo_peer.is_visible = False

    extra = MagicMock()
    extra.uid = "speaker-extra"
    extra.player_name = "Office"
    extra.is_visible = True

    current_group = MagicMock()
    current_group.coordinator = coordinator
    current_group.members = {coordinator, invisible_satellite, invisible_stereo_peer, extra}
    coordinator.group = current_group

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    SonosPlayerAdapter(group=group)

    kitchen.join.assert_called_once_with(coordinator)
    extra.unjoin.assert_called_once_with()
    invisible_satellite.unjoin.assert_not_called()
    invisible_stereo_peer.unjoin.assert_not_called()
    mock_sharelink.assert_called_once_with(coordinator)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_partial_group_prunes_extras_but_keeps_missing_desired_members(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}

    missing_desired = MagicMock()
    missing_desired.uid = "speaker-3"
    missing_desired.player_name = "Office"
    missing_desired.is_visible = True

    extra = MagicMock()
    extra.uid = "speaker-extra"
    extra.player_name = "Bedroom"
    extra.is_visible = True

    current_group = MagicMock()
    current_group.coordinator = coordinator
    current_group.members = {coordinator, missing_desired, extra}
    coordinator.group = current_group

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
        missing_member_uids=["speaker-3"],
    )

    SonosPlayerAdapter(group=group)

    kitchen.join.assert_called_once_with(coordinator)
    extra.unjoin.assert_called_once_with()
    missing_desired.unjoin.assert_not_called()
    mock_sharelink.assert_called_once_with(coordinator)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_one_member_resolved_group_preserves_single_speaker_behavior(mock_sharelink, mock_soco):
    speaker = MagicMock()
    speaker.player_name = "Living Room"
    speaker.uid = "speaker-1"
    speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    speaker.group = MagicMock(coordinator=speaker, members={speaker})
    mock_soco.return_value = speaker

    group = build_resolved_sonos_group_runtime()

    adapter = SonosPlayerAdapter(group=group)

    speaker.join.assert_not_called()
    speaker.unjoin.assert_not_called()
    mock_sharelink.assert_called_once_with(speaker)
    assert adapter.speaker is speaker


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_host_wraps_network_errors(mock_sharelink, mock_soco):
    mock_soco.side_effect = TimeoutError("timed out")

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: timed out"):
        SonosPlayerAdapter(host="192.168.1.100")

    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_group_wraps_group_enforcement_errors(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    coordinator.group = MagicMock(coordinator=coordinator, members={coordinator})

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None
    kitchen.join.side_effect = TimeoutError("join timed out")

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: join timed out"):
        SonosPlayerAdapter(group=group)

    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_group_join_failure_does_not_remove_existing_members(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    extra = MagicMock()
    extra.uid = "speaker-extra"
    extra.player_name = "Office"
    coordinator.group = MagicMock(coordinator=coordinator, members={coordinator, extra})

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None
    kitchen.join.side_effect = TimeoutError("join timed out")

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: join timed out"):
        SonosPlayerAdapter(group=group)

    extra.unjoin.assert_not_called()
    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_group_failure_rolls_back_earlier_joins(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-3"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    coordinator.group = MagicMock(coordinator=coordinator, members={coordinator})

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None

    bedroom = MagicMock()
    bedroom.uid = "speaker-2"
    bedroom.player_name = "Bedroom"
    bedroom.group = None
    bedroom.join.side_effect = TimeoutError("join timed out")

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.31": bedroom,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-3",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Bedroom", "192.168.1.31", "household-1"),
            ("speaker-3", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: join timed out"):
        SonosPlayerAdapter(group=group)

    kitchen.join.assert_called_once_with(coordinator)
    kitchen.unjoin.assert_called_once_with()
    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_group_failure_restores_joined_member_to_original_group(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-3"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    coordinator.group = MagicMock(coordinator=coordinator, members={coordinator})

    old_coordinator = MagicMock()
    old_coordinator.player_name = "Patio"
    old_coordinator.uid = "speaker-old"

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = MagicMock(coordinator=old_coordinator)

    bedroom = MagicMock()
    bedroom.uid = "speaker-2"
    bedroom.player_name = "Bedroom"
    bedroom.group = None
    bedroom.join.side_effect = TimeoutError("join timed out")

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.31": bedroom,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-3",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Bedroom", "192.168.1.31", "household-1"),
            ("speaker-3", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: join timed out"):
        SonosPlayerAdapter(group=group)

    assert kitchen.join.call_args_list == [((coordinator,),), ((old_coordinator,),)]
    kitchen.unjoin.assert_not_called()
    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_group_failure_rolls_back_earlier_removals(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = MagicMock(coordinator=coordinator)

    extra_one = MagicMock()
    extra_one.uid = "speaker-extra-1"
    extra_one.player_name = "Office"

    extra_two = MagicMock()
    extra_two.uid = "speaker-extra-2"
    extra_two.player_name = "Bedroom"
    extra_two.unjoin.side_effect = TimeoutError("unjoin timed out")

    coordinator.group = MagicMock(
        coordinator=coordinator,
        members=[coordinator, kitchen, extra_one, extra_two],
    )

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: unjoin timed out"):
        SonosPlayerAdapter(group=group)

    extra_one.unjoin.assert_called_once_with()
    extra_one.join.assert_called_once_with(coordinator)
    mock_sharelink.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_does_not_reenforce_group_after_startup(mock_sharelink, mock_soco):
    coordinator = MagicMock()
    coordinator.player_name = "Living Room"
    coordinator.uid = "speaker-2"
    coordinator.get_speaker_info.return_value = {"software_version": "1.0"}
    coordinator.group = MagicMock(coordinator=coordinator, members={coordinator})

    kitchen = MagicMock()
    kitchen.uid = "speaker-1"
    kitchen.player_name = "Kitchen"
    kitchen.group = None

    speakers_by_host = {
        "192.168.1.30": kitchen,
        "192.168.1.40": coordinator,
    }
    mock_soco.side_effect = lambda host: speakers_by_host[host]

    group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )

    adapter = SonosPlayerAdapter(group=group)
    kitchen.join.reset_mock()
    coordinator.unjoin.reset_mock()
    mock_soco.reset_mock()

    adapter.play("uri:123")

    kitchen.join.assert_not_called()
    coordinator.unjoin.assert_not_called()
    mock_soco.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate play to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.play("uri:123", shuffle=False)

    mock_speaker.clear_queue.assert_called_once_with()
    mock_sharelink.return_value.add_share_link_to_queue.assert_called_once_with("uri:123", position=1)
    mock_speaker.play_from_queue.assert_called_once_with(index=0, start=True)
    assert mock_speaker.play_mode == "NORMAL"


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_calls_underlying_sonos_player_for_non_share_link(mock_sharelink, mock_soco):
    """Should delegate play to underlying Sonos player for non-share link."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_sharelink_value = MagicMock()
    mock_sharelink.return_value = mock_sharelink_value
    mock_sharelink_value.is_share_link = lambda x: False

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.play("non-share-link", shuffle=False)

    mock_speaker.clear_queue.assert_called_once_with()
    mock_speaker.add_uri_to_queue.assert_called_once_with("non-share-link", position=1)
    mock_speaker.play_from_queue.assert_called_once_with(index=0, start=True)
    assert mock_speaker.play_mode == "NORMAL"


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_with_shuffle(mock_sharelink, mock_soco):
    """Should set shuffle mode when shuffle is True."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.play("uri:456", shuffle=True)

    assert mock_speaker.play_mode == "SHUFFLE_NOREPEAT"


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate pause to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.pause()

    mock_speaker.pause.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_uses_cached_player_name(mock_sharelink, mock_soco):
    """Should not poll Sonos for player_name while pausing."""

    class SpeakerWithNetworkedName:
        def __init__(self):
            self.get_speaker_info = MagicMock(return_value={"software_version": "1.0", "zone_name": "Living Room"})
            self.pause = MagicMock()

        @property
        def player_name(self):
            raise RequestConnectionError("No route to host")

    speaker = SpeakerWithNetworkedName()
    mock_soco.return_value = speaker

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.pause()

    speaker.pause.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_recovers_selected_group_after_ip_changes(mock_sharelink, mock_soco):
    """Should re-resolve the saved Sonos group by UID and retry the command once."""
    old_group = build_resolved_sonos_group_runtime(
        coordinator_uid="RINCON_949F3E8DD34001400",
        speakers=[("RINCON_949F3E8DD34001400", "Living Room", "192.168.1.24", "household-1")],
    )
    new_group = build_resolved_sonos_group_runtime(
        coordinator_uid="RINCON_949F3E8DD34001400",
        speakers=[("RINCON_949F3E8DD34001400", "Living Room", "192.168.1.25", "household-1")],
    )
    old_speaker = MagicMock()
    old_speaker.uid = "RINCON_949F3E8DD34001400"
    old_speaker.household_id = "household-1"
    old_speaker.group = None
    old_speaker.get_speaker_info.return_value = {"software_version": "1.0", "zone_name": "Living Room"}
    old_speaker.pause.side_effect = RequestConnectionError("No route to host")
    new_speaker = MagicMock()
    new_speaker.uid = "RINCON_949F3E8DD34001400"
    new_speaker.household_id = "household-1"
    new_speaker.group = None
    new_speaker.get_speaker_info.return_value = {"software_version": "1.0", "zone_name": "Living Room"}
    mock_soco.side_effect = lambda host: {
        "192.168.1.24": old_speaker,
        "192.168.1.25": new_speaker,
    }[host]
    sonos_playback_target_resolver = StubSonosService(resolved_group=new_group)

    adapter = SonosPlayerAdapter(
        group=old_group,
        sonos_playback_target_resolver=sonos_playback_target_resolver,
    )
    adapter.pause()

    old_speaker.pause.assert_called_once()
    new_speaker.pause.assert_called_once()
    assert adapter.speaker is new_speaker
    assert len(sonos_playback_target_resolver.calls) == 1
    assert sonos_playback_target_resolver.calls[0].coordinator_uid == "RINCON_949F3E8DD34001400"


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_raises_playback_error_when_recovery_fails(mock_sharelink, mock_soco, caplog):
    """Should report command failure after recovery cannot find the selected speaker."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.uid = "RINCON_949F3E8DD34001400"
    mock_speaker.household_id = "household-1"
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0", "zone_name": "Living Room"}
    mock_speaker.pause.side_effect = RequestConnectionError("No route to host")
    sonos_playback_target_resolver = StubSonosService(error=ValueError("not found on network"))

    adapter = SonosPlayerAdapter(
        host="192.168.1.24",
        sonos_playback_target_resolver=sonos_playback_target_resolver,
    )
    with pytest.raises(PlaybackError, match="No route to host"):
        adapter.pause()

    mock_speaker.pause.assert_called_once()
    assert "pause could not re-resolve Sonos player `Living Room`: not found on network" in caplog.text


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate resume to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.resume()

    mock_speaker.play.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_stop_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate stop to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = SonosPlayerAdapter(host="192.168.1.100")
    adapter.stop()

    mock_speaker.clear_queue.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_duplicate_speaker_names_logs_warning(mock_sharelink, mock_soco_module, caplog):
    """Should log warning when multiple speakers share the same name."""
    speaker_a = MagicMock()
    speaker_a.player_name = "Bedroom"
    speaker_b = MagicMock()
    speaker_b.player_name = "Kitchen"
    speaker_c = MagicMock()
    speaker_c.player_name = "Kitchen"
    mock_soco_module.discover.return_value = [speaker_a, speaker_b, speaker_c]

    adapter = SonosPlayerAdapter(name="Kitchen")

    assert adapter.speaker.player_name == "Kitchen"
    assert "Multiple Sonos speakers with name 'Kitchen' found. Using first match." in caplog.text


@pytest.mark.parametrize(
    "adapter_method, soco_method, args",
    [
        ("play", "play_from_queue", ("uri",)),
        ("pause", "pause", ()),
        ("resume", "play", ()),
        ("stop", "clear_queue", ()),
    ],
)
@pytest.mark.parametrize("error_code, expected_message", (("804", "bad uri"), ("701", "not available transition")))
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
def test_methods_log_and_raise_on_known_upnp_error(
    mock_soco,
    caplog,
    adapter_method,
    soco_method,
    args,
    error_code,
    expected_message,
):
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    getattr(mock_speaker, soco_method).side_effect = make_exception(error_code)

    adapter = SonosPlayerAdapter(host="192.168.1.100")

    with pytest.raises(PlaybackError):
        getattr(adapter, adapter_method)(*args)

    assert expected_message in caplog.text
    getattr(mock_speaker, soco_method).assert_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
def test_methods_log_exception_for_unknown_upnp_error(mock_soco, caplog):
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_speaker.pause.side_effect = make_exception("999")

    adapter = SonosPlayerAdapter(host="192.168.1.100")

    with pytest.raises(PlaybackError), caplog.at_level("ERROR"):
        adapter.pause()

    assert any(record.levelname == "ERROR" for record in caplog.records)
