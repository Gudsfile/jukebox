from pytest import raises

from jukebox.players import get_player
from jukebox.players.dryrun import DryRunPlayer
from jukebox.players.sonos import SonosPlayer


def test_get_dryrun_should_return_dryrun_player_type():
    """Test if the dryrun player type is returned"""
    assert get_player("dryrun") == DryRunPlayer


def test_get_player_should_return_sonos_player_type():
    """Test if the sonos player type is returned"""
    assert get_player("sonos") == SonosPlayer


def test_get_player_should_raise_an_error_if_unknown_player_name_is_provided():
    """Test if an error is raised if an unknown player name is provided"""
    with raises(ValueError) as excinfo:
        get_player("not-implemented-player")

    assert str(excinfo.value) == "The `not-implemented-player` player is not yet implemented."
