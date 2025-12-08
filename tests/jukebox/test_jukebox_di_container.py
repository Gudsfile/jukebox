from unittest.mock import MagicMock, patch

import pytest

from jukebox.adapters.inbound.config import (
    DryrunPlayerConfig,
    DryrunReaderConfig,
    JukeboxConfig,
    NfcReaderConfig,
    PlaybackConfig,
    SonosPlayerConfig,
)
from jukebox.di_container import build_jukebox


class TestBuildJukebox:
    """Tests for build_jukebox function."""

    @patch("jukebox.di_container.SonosPlayerAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_sonos_and_nfc(self, mock_library, mock_player, mocker):
        """Should build jukebox with Sonos player and NFC reader."""
        mock_nfc_instance = MagicMock()
        mock_nfc_controller_class = MagicMock(return_value=mock_nfc_instance)
        mocker.patch.dict(
            "sys.modules",
            {
                "jukebox.adapters.outbound.readers.nfc_reader_adapter": MagicMock(
                    NfcReaderAdapter=mock_nfc_controller_class
                )
            },
        )

        config = JukeboxConfig(
            library="/test/library.json",
            verbose=False,
            player=SonosPlayerConfig(type="sonos", host="192.168.1.100"),
            reader=NfcReaderConfig(type="nfc"),
            playback=PlaybackConfig(pause_duration=50, pause_delay=3),
        )

        reader, handle_tag_event = build_jukebox(config)

        # Should create library adapter
        mock_library.assert_called_once_with("/test/library.json")

        # Should create player and reader
        mock_player.assert_called_once_with(host="192.168.1.100")
        mock_nfc_controller_class.assert_called_once()

        # Should return reader and use case
        assert reader == mock_nfc_instance
        assert handle_tag_event is not None

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_dryrun(self, mock_library, mock_reader, mock_player):
        """Should build jukebox with dryrun player and reader."""
        config = JukeboxConfig(
            library="/test/library.json",
            verbose=False,
            player=DryrunPlayerConfig(type="dryrun"),
            reader=DryrunReaderConfig(type="dryrun"),
            playback=PlaybackConfig(pause_duration=100, pause_delay=5),
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_player.assert_called_once()
        mock_reader.assert_called_once()

        assert reader == mock_reader.return_value
        assert handle_tag_event is not None

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_passes_correct_parameters_to_determine_action(self, mock_library, mock_reader, mock_player):
        """Should pass pause_delay and max_pause_duration to DetermineAction."""
        config = JukeboxConfig(
            library="/test/library.json",
            verbose=False,
            player=DryrunPlayerConfig(type="dryrun"),
            reader=DryrunReaderConfig(type="dryrun"),
            playback=PlaybackConfig(pause_duration=200, pause_delay=10),
        )

        reader, handle_tag_event = build_jukebox(config)

        # Verify DetermineAction was created with correct parameters
        assert handle_tag_event.determine_action.pause_delay == 10
        assert handle_tag_event.determine_action.max_pause_duration == 200
