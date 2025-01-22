from unittest.mock import patch

from pytest import fixture

from jukebox.players.dryrun import DryRunPlayer


@fixture(scope="module")
def player():
    yield DryRunPlayer()


def test_play(player):
    """Test if the dryrun player print the message about playing"""
    with patch("builtins.print") as mock_print:
        player.play(uri="dummy-uri", shuffle=False)
    mock_print.assert_called_once_with("playing dummy-uri on player")


def test_play_with_shuffle(player):
    """Test if the dryrun player print the message about random playback"""
    with patch("builtins.print") as mock_print:
        player.play(uri="another-dummy-uri", shuffle=True)
    mock_print.assert_called_once_with("random playback of another-dummy-uri on the player")


def test_pause(player):
    """Test if the dryrun player print the message about pausing"""
    with patch("builtins.print") as mock_print:
        player.pause()
    mock_print.assert_called_once_with("pausing player")


def test_resume(player):
    """Test if the dryrun player print the message about resuming"""
    with patch("builtins.print") as mock_print:
        player.resume()
    mock_print.assert_called_once_with("resuming player")


def test_stop(player):
    """Test if the dryrun player print the message about stopping"""
    with patch("builtins.print") as mock_print:
        player.stop()
    mock_print.assert_called_once_with("stopping player")
