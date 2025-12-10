import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from jukebox.adapters.inbound.config import (
    DryrunPlayerConfig,
    DryrunReaderConfig,
    JukeboxConfig,
    NfcReaderConfig,
    PlaybackConfig,
    SonosPlayerConfig,
    parse_config,
)


class TestConfigModels:
    """Test Pydantic models for configuration."""

    def test_dryrun_player_config(self):
        config = DryrunPlayerConfig(type="dryrun")
        assert config.type == "dryrun"

    def test_sonos_player_config(self):
        config = SonosPlayerConfig(type="sonos", host="192.168.1.100")
        assert config.type == "sonos"
        assert config.host == "192.168.1.100"

    def test_sonos_player_config_requires_host(self):
        with pytest.raises(ValidationError):
            SonosPlayerConfig(type="sonos")  # type: ignore[missing-argument]

    def test_dryrun_reader_config(self):
        config = DryrunReaderConfig(type="dryrun")
        assert config.type == "dryrun"

    def test_nfc_reader_config(self):
        config = NfcReaderConfig(type="nfc")
        assert config.type == "nfc"

    def test_playback_config_defaults(self):
        config = PlaybackConfig()
        assert config.pause_duration == 900
        assert config.pause_delay == 1

    def test_playback_config_custom_values(self):
        config = PlaybackConfig(pause_duration=300, pause_delay=2)
        assert config.pause_duration == 300
        assert config.pause_delay == 2

    def test_jukebox_config_with_dryrun(self):
        config = JukeboxConfig(
            library="/path/to/library.json",
            verbose=True,
            player=DryrunPlayerConfig(type="dryrun"),
            reader=DryrunReaderConfig(type="dryrun"),
            playback=PlaybackConfig(),
        )
        assert config.library == "/path/to/library.json"
        assert config.verbose is True
        assert config.player.type == "dryrun"
        assert config.reader.type == "dryrun"

    def test_jukebox_config_with_sonos_and_nfc(self):
        config = JukeboxConfig(
            library="/path/to/library.json",
            verbose=False,
            player=SonosPlayerConfig(type="sonos", host="192.168.1.100"),
            reader=NfcReaderConfig(type="nfc"),
            playback=PlaybackConfig(pause_duration=600),
        )
        assert config.library == "/path/to/library.json"
        assert config.verbose is False
        assert config.player.type == "sonos"
        assert config.player.host == "192.168.1.100"
        assert config.reader.type == "nfc"
        assert config.playback.pause_duration == 600


class TestParseConfig:
    """Test parse_config function."""

    @patch("sys.argv", ["jukebox", "dryrun", "dryrun"])
    def test_parse_config_dryrun_minimal(self):
        config = parse_config()
        assert config.player.type == "dryrun"
        assert config.reader.type == "dryrun"
        assert config.verbose is False
        assert config.playback.pause_duration == 900
        assert config.playback.pause_delay == 1

    @patch("sys.argv", ["jukebox", "sonos", "nfc", "--sonos-host", "192.168.1.50"])
    def test_parse_config_sonos_with_cli_host(self):
        config = parse_config()
        assert config.player.type == "sonos"
        assert config.player.host == "192.168.1.50"
        assert config.reader.type == "nfc"

    @patch.dict(os.environ, {"JUKEBOX_SONOS_HOST": "192.168.1.200"})
    @patch("sys.argv", ["jukebox", "sonos", "nfc"])
    @patch("logging.Logger.warning")
    def test_parse_config_sonos_with_env_host(self, mock_warning):
        config = parse_config()
        assert mock_warning.call_count == 0
        assert config.player.type == "sonos"
        assert config.player.host == "192.168.1.200"

    @patch.dict(os.environ, {"SONOS_HOST": "192.168.1.200"})
    @patch("sys.argv", ["jukebox", "sonos", "nfc"])
    @patch("logging.Logger.warning")
    def test_parse_config_sonos_with_deprecated_env_host(self, mock_warning):
        config = parse_config()
        assert mock_warning.call_count == 1
        assert config.player.type == "sonos"
        assert config.player.host == "192.168.1.200"

    @patch.dict(os.environ, {"JUKEBOX_SONOS_HOST": "192.168.1.200"})
    @patch("sys.argv", ["jukebox", "sonos", "nfc", "--sonos-host", "192.168.1.99"])
    def test_parse_config_cli_overrides_env(self):
        config = parse_config()
        assert config.player.host == "192.168.1.99"

    @patch("sys.argv", ["jukebox", "sonos", "nfc"])
    def test_parse_config_sonos_missing_host_raises_error(self):
        with pytest.raises(SystemExit):
            parse_config()

    @patch.dict(os.environ, {"JUKEBOX_LIBRARY_PATH": "/custom/library.json"})
    @patch("sys.argv", ["jukebox", "dryrun", "dryrun"])
    @patch("logging.Logger.warning")
    def test_parse_config_library_from_env(self, mock_warning):
        config = parse_config()
        assert mock_warning.call_count == 0
        assert config.library == "/custom/library.json"

    @patch.dict(os.environ, {"LIBRARY_PATH": "/custom/library.json"})
    @patch("sys.argv", ["jukebox", "dryrun", "dryrun"])
    @patch("logging.Logger.warning")
    def test_parse_config_library_from_deprecated_env(self, mock_warning):
        config = parse_config()
        assert mock_warning.call_count == 1
        assert config.library == "/custom/library.json"

    @patch("sys.argv", ["jukebox", "dryrun", "dryrun", "-l", "/cli/library.json"])
    def test_parse_config_library_from_cli(self):
        config = parse_config()
        assert config.library == "/cli/library.json"

    @patch.dict(os.environ, {"JUKEBOX_LIBRARY_PATH": "/env/library.json"})
    @patch("sys.argv", ["jukebox", "dryrun", "dryrun", "-l", "/cli/library.json"])
    def test_parse_config_library_cli_overrides_env(self):
        config = parse_config()
        assert config.library == "/cli/library.json"

    @patch("sys.argv", ["jukebox", "dryrun", "dryrun", "-v"])
    def test_parse_config_verbose_flag(self):
        config = parse_config()
        assert config.verbose is True

    @patch("sys.argv", ["jukebox", "dryrun", "dryrun", "--pause-duration", "300", "--pause-delay", "2"])
    def test_parse_config_custom_playback_params(self):
        config = parse_config()
        assert config.playback.pause_duration == 300
        assert config.playback.pause_delay == 2

    @patch("sys.argv", ["jukebox", "dryrun", "nfc"])
    def test_parse_config_mixed_player_reader(self):
        config = parse_config()
        assert config.player.type == "dryrun"
        assert config.reader.type == "nfc"
