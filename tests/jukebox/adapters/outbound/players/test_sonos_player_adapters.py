from typing import Any
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
from requests.exceptions import ConnectionError as RequestConnectionError
from soco.exceptions import SoCoUPnPException

from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.domain.errors import CannotResumeError, PlaybackError
from jukebox.settings.errors import InvalidSettingsError
from tests.jukebox.settings._helpers import StubSonosService, build_resolved_sonos_group_runtime


def make_exception(code: str):
    return SoCoUPnPException(f"UPnP Error {code} received", code, f"<errorCode>{code}</errorCode>")


def track_play_calls(mock_speaker: MagicMock, mock_sharelink: MagicMock) -> MagicMock:
    """Record the queue commands and `play_mode` assignments of `play()` in one ordered list."""
    tracker = MagicMock()
    play_mode = PropertyMock(return_value="NORMAL")
    type(mock_speaker).play_mode = play_mode
    tracker.attach_mock(play_mode, "play_mode")
    tracker.attach_mock(mock_speaker.clear_queue, "clear_queue")
    tracker.attach_mock(mock_speaker.add_uri_to_queue, "add_uri_to_queue")
    tracker.attach_mock(mock_sharelink.return_value.add_share_link_to_queue, "add_share_link_to_queue")
    tracker.attach_mock(mock_speaker.play_from_queue, "play_from_queue")
    return tracker


def recorded_play_calls(tracker: MagicMock) -> list:
    # Reading `play_mode` back is allowed, only assignments matter
    return [c for c in tracker.mock_calls if c != call.play_mode()]


def set_queue(mock_speaker: MagicMock, uris: list[str]) -> None:
    """Make the speaker report a queue holding these item URIs, in order."""
    items = []
    for uri in uris:
        item = MagicMock()
        item.get_uri.return_value = uri
        item.resources = [MagicMock(uri=uri)]
        items.append(item)
    mock_speaker.get_queue.return_value = items
    mock_speaker.queue_size = len(items)


def build_adapter(**kwargs: Any) -> SonosPlayerAdapter:
    kwargs.setdefault("sonos_playback_target_resolver", MagicMock())
    return SonosPlayerAdapter(**kwargs)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_host(mock_sharelink, mock_soco):
    build_adapter(host="192.168.1.100")
    mock_soco.assert_called_once_with("192.168.1.100")
    mock_sharelink.assert_called_once_with(mock_soco.return_value)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_without_host_triggers_discovery(mock_sharelink, mock_soco_module):
    """Should use auto-discovery when no host is provided."""
    mock_speaker = MagicMock()
    mock_speaker.player_name = "Living Room"
    mock_soco_module.discover.return_value = {mock_speaker}

    adapter = build_adapter()

    mock_soco_module.discover.assert_called_once()
    mock_sharelink.assert_called_once_with(mock_speaker)
    assert adapter.speaker is mock_speaker


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.soco")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_without_host_raises_when_no_speakers_found(mock_sharelink, mock_soco_module):
    """Should raise InvalidSettingsError when discovery finds no speakers."""
    mock_soco_module.discover.return_value = None

    with pytest.raises(InvalidSettingsError, match="No Sonos speakers found on the network"):
        build_adapter()

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

    adapter = build_adapter()

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

    adapter = build_adapter(name="Living Room")

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
        build_adapter(name="Bedroom")

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

    adapter = build_adapter(group=group)

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

    build_adapter(group=group)

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

    build_adapter(group=group)

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

    adapter = build_adapter(group=group)

    speaker.join.assert_not_called()
    speaker.unjoin.assert_not_called()
    mock_sharelink.assert_called_once_with(speaker)
    assert adapter.speaker is speaker


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_host_wraps_network_errors(mock_sharelink, mock_soco):
    mock_soco.side_effect = TimeoutError("timed out")

    with pytest.raises(InvalidSettingsError, match="Failed to initialize Sonos player: timed out"):
        build_adapter(host="192.168.1.100")

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
        build_adapter(group=group)

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
        build_adapter(group=group)

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
        build_adapter(group=group)

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
        build_adapter(group=group)

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
        build_adapter(group=group)

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

    adapter = build_adapter(group=group)
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

    adapter = build_adapter(host="192.168.1.100")
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

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("non-share-link", shuffle=False)

    mock_speaker.clear_queue.assert_called_once_with()
    mock_speaker.add_uri_to_queue.assert_called_once_with("non-share-link", position=1)
    mock_speaker.play_from_queue.assert_called_once_with(index=0, start=True)
    assert mock_speaker.play_mode == "NORMAL"


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_without_shuffle_sets_normal_mode_before_filling_queue(mock_sharelink, mock_soco):
    """Should switch to normal mode on the empty queue, then play the queue from its first track."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    tracker = track_play_calls(mock_speaker, mock_sharelink)

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:456", shuffle=False)

    assert recorded_play_calls(tracker) == [
        call.clear_queue(),
        call.play_mode("NORMAL"),
        call.add_share_link_to_queue("uri:456", position=1),
        call.play_from_queue(index=0, start=True),
        call.play_mode("NORMAL"),
    ]


@patch("random.randrange", return_value=7)
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_with_shuffle_starts_from_random_track_then_shuffles(mock_sharelink, mock_soco, mock_randrange):
    """Should start from a random track, then shuffle the rest of the queue after it (#454)."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_speaker.queue_size = 12
    tracker = track_play_calls(mock_speaker, mock_sharelink)

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:456", shuffle=True)

    assert recorded_play_calls(tracker) == [
        call.clear_queue(),
        call.play_mode("NORMAL"),
        call.add_share_link_to_queue("uri:456", position=1),
        call.play_from_queue(index=7, start=True),
        call.play_mode("SHUFFLE_NOREPEAT"),
    ]


@patch("random.randrange", return_value=0)
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_with_shuffle_draws_start_track_from_whole_queue(mock_sharelink, mock_soco, mock_randrange):
    """Should draw the start index from the queue size, not from the index returned when enqueuing."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_speaker.queue_size = 12
    # soco returns the queue index of the first enqueued track, not the number of tracks
    mock_sharelink.return_value.add_share_link_to_queue.return_value = 1

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:456", shuffle=True)

    mock_randrange.assert_called_once_with(12)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_play_with_shuffle_raises_playback_error_when_uri_adds_nothing_to_queue(mock_sharelink, mock_soco):
    """Should raise a PlaybackError without playing when the speaker refuses to enqueue the URI."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    # e.g. an empty playlist or an unavailable album: the speaker fails before the queue size is read
    mock_sharelink.return_value.add_share_link_to_queue.side_effect = make_exception("800")

    adapter = build_adapter(host="192.168.1.100")
    with pytest.raises(PlaybackError):
        adapter.play("uri:456", shuffle=True)

    mock_speaker.play_from_queue.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate pause to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = build_adapter(host="192.168.1.100")
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

    adapter = build_adapter(host="192.168.1.100")
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

    adapter = build_adapter(
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

    adapter = build_adapter(
        host="192.168.1.24",
        sonos_playback_target_resolver=sonos_playback_target_resolver,
    )
    with pytest.raises(PlaybackError, match="No route to host"):
        adapter.pause()

    mock_speaker.pause.assert_called_once()
    assert "pause could not re-resolve Sonos player `Living Room`: not found on network" in caplog.text


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_reports_group_switch_failure_separately(mock_sharelink, mock_soco, caplog):
    """Should distinguish successful target resolution from a later failed group switch."""
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

    def build_soco(host: str):
        if host == "192.168.1.24":
            return old_speaker
        if host == "192.168.1.25":
            raise TimeoutError("switch timed out")
        raise AssertionError(f"unexpected Sonos host: {host}")

    mock_soco.side_effect = build_soco
    sonos_playback_target_resolver = StubSonosService(resolved_group=new_group)

    adapter = build_adapter(
        group=old_group,
        sonos_playback_target_resolver=sonos_playback_target_resolver,
    )
    with pytest.raises(PlaybackError, match="No route to host"):
        adapter.pause()

    old_speaker.pause.assert_called_once()
    assert "pause recovered Sonos player `Living Room` but failed during group switch: switch timed out" in caplog.text
    assert "pause could not re-resolve Sonos player `Living Room`" not in caplog.text


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_pause_does_not_swallow_group_switch_invariant_failures(mock_sharelink, mock_soco, caplog):
    """Should not treat adapter invariant failures as rediscovery misses."""
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
    mock_soco.side_effect = lambda host: {
        "192.168.1.24": old_speaker,
        "192.168.1.25": new_speaker,
    }[host]
    sonos_playback_target_resolver = StubSonosService(resolved_group=new_group)

    adapter = build_adapter(
        group=old_group,
        sonos_playback_target_resolver=sonos_playback_target_resolver,
    )
    with (
        patch(
            "jukebox.adapters.outbound.players.sonos_player_adapter.playback_target_from_runtime_group",
            side_effect=ValueError("invalid playback target"),
        ),
        pytest.raises(ValueError, match="invalid playback target"),
    ):
        adapter.pause()

    assert "pause could not re-resolve Sonos player `Living Room`" not in caplog.text


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_calls_underlying_sonos_player_when_queue_is_unchanged(mock_sharelink, mock_soco):
    """Should resume when the queue still holds what the last play() put in it."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1", "x-sonos:track-2"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    adapter.resume()

    mock_speaker.play.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_when_queue_was_replaced(mock_sharelink, mock_soco, caplog):
    """Should not resume music started outside jukebox (e.g. from the Sonos app) after play()."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1", "x-sonos:track-2"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    set_queue(mock_speaker, ["x-sonos:other-1", "x-sonos:other-2"])

    with caplog.at_level("INFO", logger="jukebox"), pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_not_called()
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_when_queue_was_shortened(mock_sharelink, mock_soco):
    """Should not resume when the queue keeps the same first track but lost some of the others."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1", "x-sonos:track-2"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    set_queue(mock_speaker, ["x-sonos:track-1"])

    with pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_when_queue_was_emptied(mock_sharelink, mock_soco):
    """Should not resume when the queue was cleared, without waiting for Sonos to reject play()."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    set_queue(mock_speaker, [])

    with pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_tolerates_tracks_appended_to_the_queue(mock_sharelink, mock_soco):
    """Should still resume when tracks were only added after the ones play() queued."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1", "x-sonos:track-2"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    set_queue(mock_speaker, ["x-sonos:track-1", "x-sonos:track-2", "x-sonos:added-1"])
    adapter.resume()

    mock_speaker.play.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_compares_the_queue_not_the_played_share_link(mock_sharelink, mock_soco):
    """Should resume a share link, whose URI differs from the items it puts in the queue."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_sharelink.return_value.is_share_link.return_value = True
    set_queue(mock_speaker, ["x-sonos-spotify:spotify%3atrack%3a1", "x-sonos-spotify:spotify%3atrack%3a2"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("https://open.spotify.com/album/abc")
    adapter.resume()

    mock_speaker.play.assert_called_once()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_without_previous_play(mock_sharelink, mock_soco):
    """Should not resume whatever the speaker holds when jukebox never played anything on it."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1"])

    adapter = build_adapter(host="192.168.1.100")

    with pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_after_stop(mock_sharelink, mock_soco):
    """Should forget the last play() once stop() cleared the queue, even if the same tracks are queued again."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1"])

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")
    adapter.stop()

    with pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_not_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_logs_and_raises_on_bad_uri(mock_sharelink, mock_soco, caplog):
    """Should report a non-701 UPnP error on resume as a playback error."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1"])
    mock_speaker.play.side_effect = make_exception("804")

    adapter = build_adapter(host="192.168.1.100")
    adapter.play("uri:123")

    with pytest.raises(PlaybackError) as exc_info:
        adapter.resume()

    assert not isinstance(exc_info.value, CannotResumeError)
    assert "bad uri" in caplog.text
    mock_speaker.play.assert_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_resume_raises_cannot_resume_on_upnp_701(mock_sharelink, mock_soco, caplog):
    """Should report a 701 on resume as nothing to resume, without recovery or warning."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    set_queue(mock_speaker, ["x-sonos:track-1"])
    mock_speaker.play.side_effect = make_exception("701")
    resolver = MagicMock()

    adapter = build_adapter(host="192.168.1.100", sonos_playback_target_resolver=resolver)
    adapter.play("uri:123")

    with caplog.at_level("INFO", logger="jukebox"), pytest.raises(CannotResumeError):
        adapter.resume()

    mock_speaker.play.assert_called_once()
    resolver.assert_not_called()
    assert "has nothing to resume" in caplog.text
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_stop_calls_underlying_sonos_player(mock_sharelink, mock_soco):
    """Should delegate stop to underlying Sonos player."""
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}

    adapter = build_adapter(host="192.168.1.100")
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

    adapter = build_adapter(name="Kitchen")

    assert adapter.speaker.player_name == "Kitchen"
    assert "Multiple Sonos speakers with name 'Kitchen' found. Using first match." in caplog.text


@pytest.mark.parametrize(
    "adapter_method, soco_method, args, error_code, expected_message",
    [
        pytest.param("play", "play_from_queue", ("uri",), "804", "bad uri", id="play_with_bad_uri"),
        pytest.param(
            "play",
            "play_from_queue",
            ("uri",),
            "701",
            "not available transition",
            id="play_with_unavailable_transition",
        ),
        pytest.param("pause", "pause", (), "804", "bad uri", id="pause_with_bad_uri"),
        # pause tolerates 701, see test_pause_ignores_upnp_701_when_player_is_not_playing
        # resume needs a previous play, see test_resume_logs_and_raises_on_bad_uri
        # and test_resume_raises_cannot_resume_on_upnp_701
        pytest.param("stop", "clear_queue", (), "804", "bad uri", id="stop_with_bad_uri"),
        pytest.param(
            "stop", "clear_queue", (), "701", "not available transition", id="stop_with_unavailable_transition"
        ),
    ],
)
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

    adapter = build_adapter(host="192.168.1.100")

    with pytest.raises(PlaybackError):
        getattr(adapter, adapter_method)(*args)

    assert expected_message in caplog.text
    getattr(mock_speaker, soco_method).assert_called()


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
def test_pause_ignores_upnp_701_when_player_is_not_playing(mock_soco, caplog):
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_speaker.pause.side_effect = make_exception("701")

    adapter = build_adapter(host="192.168.1.100")

    with caplog.at_level("INFO"):
        adapter.pause()

    mock_speaker.pause.assert_called_once()
    assert "nothing to pause" in caplog.text
    assert not any(record.levelname == "WARNING" for record in caplog.records)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
def test_methods_log_exception_for_unknown_upnp_error(mock_soco, caplog):
    mock_speaker = MagicMock()
    mock_soco.return_value = mock_speaker
    mock_speaker.get_speaker_info.return_value = {"software_version": "1.0"}
    mock_speaker.pause.side_effect = make_exception("999")

    adapter = build_adapter(host="192.168.1.100")

    with pytest.raises(PlaybackError), caplog.at_level("ERROR"):
        adapter.pause()

    assert any(record.levelname == "ERROR" for record in caplog.records)
