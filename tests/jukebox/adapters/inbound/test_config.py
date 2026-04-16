from unittest.mock import patch

import pytest

from jukebox.adapters.inbound.config import JukeboxCliConfig, parse_config


@patch("sys.argv", ["jukebox"])
def test_parse_config_without_overrides():
    config = parse_config()

    assert config == JukeboxCliConfig()


@patch("sys.argv", ["jukebox", "--player", "sonos", "--reader", "pn532", "--sonos-host", "192.168.1.50"])
def test_parse_config_with_player_reader_and_host_overrides():
    config = parse_config()

    assert config.player == "sonos"
    assert config.reader == "pn532"
    assert config.sonos_host == "192.168.1.50"
    assert config.sonos_name is None


@patch("sys.argv", ["jukebox", "--player", "sonos", "--reader", "pn532", "--sonos-name", "Living Room"])
def test_parse_config_with_sonos_name_override():
    config = parse_config()

    assert config.player == "sonos"
    assert config.reader == "pn532"
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


@patch("sys.argv", ["jukebox", "--reader", "pn532"])
def test_parse_config_allows_reader_only_override_flag():
    config = parse_config()

    assert config.player is None
    assert config.reader == "pn532"


@patch("sys.argv", ["jukebox", "--sonos-host", "192.168.1.1", "--sonos-name", "Living Room"])
def test_parse_config_rejects_sonos_host_and_name_together():
    with pytest.raises(SystemExit):
        parse_config()


@patch("sys.argv", ["jukebox", "--pn532-spi-reset", "25", "--pn532-spi-cs", "8", "--pn532-spi-irq", "24"])
def test_parse_config_with_pn532_spi_pin_overrides():
    config = parse_config()

    assert config.pn532_spi_reset == 25
    assert config.pn532_spi_cs == 8
    assert config.pn532_spi_irq == 24


@patch("sys.argv", ["jukebox"])
def test_parse_config_pn532_overrides_default_to_none():
    config = parse_config()

    assert config.pn532_spi_reset is None
    assert config.pn532_spi_cs is None
    assert config.pn532_spi_irq is None


@pytest.mark.parametrize("subcommand", ["settings", "api", "ui", "library"])
def test_parse_config_rejects_admin_subcommands(subcommand):
    with patch("sys.argv", ["jukebox", subcommand]), pytest.raises(SystemExit) as err:
        parse_config()

    assert err.value.code == 2
