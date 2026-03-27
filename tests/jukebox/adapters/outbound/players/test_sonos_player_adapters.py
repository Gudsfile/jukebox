from unittest.mock import MagicMock, patch

import pytest

from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter
from jukebox.settings.errors import InvalidSettingsError
from tests.jukebox.settings._helpers import build_resolved_sonos_group_runtime


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
