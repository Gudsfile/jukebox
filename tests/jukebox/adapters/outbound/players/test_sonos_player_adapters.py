from unittest.mock import MagicMock, patch

import pytest

from jukebox.adapters.outbound.players.sonos_player_adapter import SonosPlayerAdapter


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_with_host(mock_sharelink, mock_soco):
    SonosPlayerAdapter(host="192.168.1.100")
    mock_soco.assert_called_once_with("192.168.1.100")
    mock_sharelink.assert_called_once_with(mock_soco.return_value)


@patch("jukebox.adapters.outbound.players.sonos_player_adapter.SoCo")
@patch("jukebox.adapters.outbound.players.sonos_player_adapter.ShareLinkPlugin")
def test_init_without_host(mock_sharelink, mock_soco):
    """Should raise ValueError when host is empty or None."""
    with pytest.raises(ValueError, match="Host must be provided for Sonos player"):
        SonosPlayerAdapter(host="")
    with pytest.raises(ValueError, match="Host must be provided for Sonos player"):
        SonosPlayerAdapter(host=None)  # ty: ignore[invalid-argument-type]
    mock_soco.assert_not_called()
    mock_sharelink.assert_not_called()


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
