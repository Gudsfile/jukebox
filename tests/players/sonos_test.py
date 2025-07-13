import logging
import os
from unittest.mock import MagicMock, patch

from pytest import fixture, raises

LOGGER = logging.getLogger(__name__)


@fixture(scope="function")
def mock_sonos_player():
    with patch("jukebox.players.sonos.SoCo"):
        with patch("jukebox.players.sonos.ShareLinkPlugin"):
            from jukebox.players.sonos import SonosPlayer

            mocked_player = SonosPlayer("192.168.0.1")
            mocked_speaker = MagicMock(player_name="MockedPlayer")
            mocked_sharelink = MagicMock(
                soco=mocked_speaker, is_share_link=lambda x: True if x.startswith("sharelink:") else False
            )
            mocked_player.sharelink = mocked_sharelink
            mocked_player.speaker = mocked_speaker
            yield mocked_player, mocked_speaker, mocked_sharelink


def test_init_should_use_provided_host_to_connect():
    """Test if the host is set to the value of the argument"""
    with patch.dict(os.environ, {}):
        with patch("jukebox.players.sonos.SoCo") as mocked_speaker:
            with patch("jukebox.players.sonos.ShareLinkPlugin") as mocked_sharelink:
                from jukebox.players.sonos import SonosPlayer

                SonosPlayer("host-from-arg")
    mocked_speaker.assert_called_once_with("host-from-arg")
    mocked_sharelink.assert_called_once_with(mocked_speaker.return_value)


def test_init_should_prefer_provided_host_over_env_var():
    """Test if the host is set to the value of the argument if provided even if the SONOS_HOST environment variable is set"""
    with patch.dict(os.environ, {"SONOS_HOST": "host-from-env-var"}):
        with patch("jukebox.players.sonos.SoCo") as mocked_speaker:
            with patch("jukebox.players.sonos.ShareLinkPlugin") as mocked_sharelink:
                from jukebox.players.sonos import SonosPlayer

                SonosPlayer("host-from-arg")
    mocked_speaker.assert_called_once_with("host-from-arg")
    mocked_sharelink.assert_called_once_with(mocked_speaker.return_value)


def test_init_should_user_env_var_if_provided_host_is_none():
    """Test if the host is set to the value of the SONOS_HOST environment variable"""
    with patch.dict(os.environ, {"SONOS_HOST": "host-from-env-var"}):
        with patch("jukebox.players.sonos.SoCo") as mocked_speaker:
            with patch("jukebox.players.sonos.ShareLinkPlugin") as mocked_sharelink:
                from jukebox.players.sonos import SonosPlayer

                SonosPlayer()
    mocked_speaker.assert_called_once_with("host-from-env-var")
    mocked_sharelink.assert_called_once_with(mocked_speaker.return_value)


def test_init_should_raise_an_error_if_no_host_is_provided():
    """Test if an error is raised if no host is provided"""
    with patch.dict(os.environ, {}, clear=True):
        from jukebox.players.sonos import SonosPlayer

        with raises(ValueError) as excinfo:
            SonosPlayer()
    assert (
        str(excinfo.value) == "Host must be provided, either as an argument or in the SONOS_HOST environment variable."
    )


def test_play_as_normal_mode(mock_sonos_player, caplog):
    """Test if the queue is clear, the uri is added to the queue, the speaker is set to normal mode and the queue is played"""
    mocked_player, mocked_speaker, mocked_sharelink = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.play(uri="dummy-uri", shuffle=False)

    assert "Playing `dummy-uri` on the player `MockedPlayer`" in caplog.text
    mocked_speaker.clear_queue.assert_called_once_with()
    mocked_speaker.add_uri_to_queue.assert_called_once_with("dummy-uri", position=1)
    assert mocked_speaker.play_mode == "NORMAL"
    mocked_speaker.play_from_queue.assert_called_once_with(index=0, start=True)


def test_play_with_shuffle(mock_sonos_player, caplog):
    """Test if the queue is clear, the uri is added to the queue, the speaker is set to shuffle mode and the queue is played"""
    mocked_player, mocked_speaker, mocked_sharelink = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.play(uri="dummy-uri", shuffle=True)

    assert "Playing `dummy-uri` on the player `MockedPlayer`" in caplog.text
    mocked_speaker.clear_queue.assert_called_once_with()
    mocked_speaker.add_uri_to_queue.assert_called_once_with("dummy-uri", position=1)
    assert mocked_speaker.play_mode == "SHUFFLE_NOREPEAT"
    mocked_speaker.play_from_queue.assert_called_once_with(index=0, start=True)


def test_play_with_sharelink_compatible_uri(mock_sonos_player, caplog):
    """Test if ShareLink compatible uri is add to the queue"""
    mocked_player, mocked_speaker, mocked_sharelink = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.play(uri="sharelink:uri", shuffle=True)

    assert "Playing `sharelink:uri` on the player `MockedPlayer`" in caplog.text
    mocked_speaker.clear_queue.assert_called_once_with()
    mocked_sharelink.add_share_link_to_queue.assert_called_once_with("sharelink:uri", position=1)
    assert mocked_speaker.play_mode == "SHUFFLE_NOREPEAT"
    mocked_speaker.play_from_queue.assert_called_once_with(index=0, start=True)


def test_pause(mock_sonos_player, caplog):
    """Test if pause is called on the speaker"""
    mocked_player, mocked_speaker, _ = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.pause()

    assert "Pausing player `MockedPlayer`" in caplog.text
    mocked_speaker.pause.assert_called_once_with()


def test_resume(mock_sonos_player, caplog):
    """Test if play is called on the speaker"""
    mocked_player, mocked_speaker, _ = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.resume()

    assert "Resuming player `MockedPlayer`" in caplog.text
    mocked_speaker.play.assert_called_once_with()


def test_stop(mock_sonos_player, caplog):
    """Test if the speaker is cleared of its queue"""
    mocked_player, mocked_speaker, _ = mock_sonos_player

    with caplog.at_level(logging.INFO):
        mocked_player.stop()

    assert "Stopping player `MockedPlayer` and clearing its queue" in caplog.text
    mocked_speaker.clear_queue.assert_called_once_with()
