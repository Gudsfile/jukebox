from unittest.mock import MagicMock, patch

import pytest

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

        reader, handle_tag_event = build_jukebox(
            library_path="/test/library.json",
            player_type="sonos",
            reader_type="nfc",
            pause_duration=50,
            pause_delay=3,
        )

        # Should create library adapter
        mock_library.assert_called_once_with("/test/library.json")

        # Should create player and reader
        mock_player.assert_called_once()
        mock_nfc_controller_class.assert_called_once()

        # Should return reader and use case
        assert reader == mock_nfc_instance
        assert handle_tag_event is not None

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_dryrun(self, mock_library, mock_reader, mock_player):
        """Should build jukebox with dryrun player and reader."""
        reader, handle_tag_event = build_jukebox(
            library_path="/test/library.json",
            player_type="dryrun",
            reader_type="dryrun",
            pause_duration=100,
            pause_delay=5,
        )

        mock_library.assert_called_once_with("/test/library.json")
        mock_player.assert_called_once()
        mock_reader.assert_called_once()

        assert reader == mock_reader.return_value
        assert handle_tag_event is not None

    @patch("jukebox.di_container.JsonLibraryAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    def test_build_jukebox_raises_error_for_unknown_player(self, mock_reader, mock_library):
        """Should raise error for unknown player type."""
        with pytest.raises(ValueError, match="Unknown player type: unknown"):
            build_jukebox(
                library_path="/test/library.json",
                player_type="unknown",
                reader_type="dryrun",
                pause_duration=50,
                pause_delay=3,
            )

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_raises_error_for_unknown_reader(self, mock_library, mock_player):
        """Should raise error for unknown reader type."""
        with pytest.raises(ValueError, match="Unknown reader type: unknown"):
            build_jukebox(
                library_path="/test/library.json",
                player_type="dryrun",
                reader_type="unknown",
                pause_duration=50,
                pause_delay=3,
            )

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_passes_correct_parameters_to_determine_action(self, mock_library, mock_reader, mock_player):
        """Should pass pause_delay and max_pause_duration to DetermineAction."""
        reader, handle_tag_event = build_jukebox(
            library_path="/test/library.json",
            player_type="dryrun",
            reader_type="dryrun",
            pause_duration=200,
            pause_delay=10,
        )

        # Verify DetermineAction was created with correct parameters
        assert handle_tag_event.determine_action.pause_delay == 10
        assert handle_tag_event.determine_action.max_pause_duration == 200
