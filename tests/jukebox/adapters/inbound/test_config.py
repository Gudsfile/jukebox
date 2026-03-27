from unittest.mock import patch

import pytest

from jukebox.adapters.inbound.config import JukeboxCliConfig, parse_config


@patch("sys.argv", ["jukebox"])
def test_parse_config_without_overrides():
    config = parse_config()

    assert config == JukeboxCliConfig()


@patch("sys.argv", ["jukebox", "sonos", "nfc", "--sonos-host", "192.168.1.50"])
def test_parse_config_with_player_reader_and_host_overrides():
    config = parse_config()

    assert config.player == "sonos"
    assert config.reader == "nfc"
    assert config.sonos_host == "192.168.1.50"
    assert config.sonos_name is None


@patch("sys.argv", ["jukebox", "sonos", "nfc", "--sonos-name", "Living Room"])
def test_parse_config_with_sonos_name_override():
    config = parse_config()

    assert config.player == "sonos"
    assert config.reader == "nfc"
    assert config.sonos_host is None
    assert config.sonos_name == "Living Room"


@patch("sys.argv", ["jukebox", "--pause-duration", "300", "--pause-delay", "0.2"])
def test_parse_config_with_playback_overrides():
    config = parse_config()

    assert config.pause_duration_seconds == 300
    assert config.pause_delay_seconds == 0.2


@patch("sys.argv", ["jukebox", "-l", "/cli/library.json", "-v"])
def test_parse_config_with_library_and_verbose_flags():
    config = parse_config()

    assert config.library == "/cli/library.json"
    assert config.verbose is True


@patch("sys.argv", ["jukebox", "dryrun"])
def test_parse_config_allows_partial_type_overrides(capsys):
    config = parse_config()

    assert config.player == "dryrun"
    assert config.reader is None
    assert (
        capsys.readouterr().err.strip()
        == "warning: positional player/reader arguments are deprecated; use --player/--reader instead"
    )


@patch("sys.argv", ["jukebox", "--reader", "nfc"])
def test_parse_config_allows_reader_only_override_flag(capsys):
    config = parse_config()

    assert config.player is None
    assert config.reader == "nfc"
    assert capsys.readouterr().err == ""


@patch("sys.argv", ["jukebox", "dryrun", "dryrun", "--reader", "nfc"])
def test_parse_config_reader_flag_overrides_positional_reader(capsys):
    config = parse_config()

    assert config.player == "dryrun"
    assert config.reader == "nfc"
    assert (
        capsys.readouterr().err.strip()
        == "warning: positional player/reader arguments are deprecated; use --player/--reader instead"
    )


@patch("sys.argv", ["jukebox", "--sonos-host", "192.168.1.1", "--sonos-name", "Living Room"])
def test_parse_config_rejects_sonos_host_and_name_together():
    with pytest.raises(SystemExit):
        parse_config()


@pytest.mark.parametrize("subcommand", ["settings", "api", "ui", "library"])
def test_parse_config_rejects_admin_subcommands(subcommand):
    with patch("sys.argv", ["jukebox", subcommand]), pytest.raises(SystemExit) as err:
        parse_config()

    assert err.value.code == 2
