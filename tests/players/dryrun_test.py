import logging

from pytest import fixture

from jukebox.players.dryrun import DryRunPlayer

LOGGER = logging.getLogger(__name__)


@fixture(scope="module")
def player():
    yield DryRunPlayer()


def test_play(player, caplog):
    """Test if the dryrun player log the message about playing"""
    with caplog.at_level(logging.INFO):
        player.play(uri="dummy-uri", shuffle=False)
    assert "Playing `dummy-uri` on player" in caplog.text


def test_play_with_shuffle(player, caplog):
    """Test if the dryrun player log the message about random playback"""
    with caplog.at_level(logging.INFO):
        player.play(uri="another-dummy-uri", shuffle=True)
    assert "Random playback of `another-dummy-uri` on the player" in caplog.text


def test_pause(player, caplog):
    """Test if the dryrun player log the message about pausing"""
    with caplog.at_level(logging.INFO):
        player.pause()
    assert "Pausing player" in caplog.text


def test_resume(player, caplog):
    """Test if the dryrun player log the message about resuming"""
    with caplog.at_level(logging.INFO):
        player.resume()
    assert "Resuming player" in caplog.text


def test_stop(player, caplog):
    """Test if the dryrun player log the message about stopping"""
    with caplog.at_level(logging.INFO):
        player.stop()
    assert "Stopping player" in caplog.text
