from unittest.mock import MagicMock, patch

from jukebox.di_container import build_jukebox
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.shared.config_utils import get_current_tag_path
from tests.jukebox.settings._helpers import build_resolved_sonos_group_runtime


def test_get_current_tag_path_derives_path_beside_library(tmp_path):
    library_path = tmp_path / "nested" / "library.json"

    assert get_current_tag_path(str(library_path)) == str(tmp_path / "nested" / "current-tag.txt")


class TestBuildJukebox:
    @patch("jukebox.di_container.SonosPlayerAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_sonos_and_nfc(self, mock_library, mock_current_tag, mock_player, mocker):
        mock_nfc_instance = MagicMock()
        mock_nfc_class = MagicMock(return_value=mock_nfc_instance)
        mocker.patch.dict(
            "sys.modules",
            {"jukebox.adapters.outbound.readers.nfc_reader_adapter": MagicMock(NfcReaderAdapter=mock_nfc_class)},
        )

        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="sonos",
            sonos_host="192.168.1.100",
            sonos_name=None,
            sonos_group=build_resolved_sonos_group_runtime(
                speakers=[("speaker-1", "Living Room", "192.168.1.100", "household-1")]
            ),
            reader_type="nfc",
            pause_duration_seconds=50,
            pause_delay_seconds=3,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.25,
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_current_tag.assert_called_once_with("/test/current-tag.txt")
        mock_player.assert_called_once_with(host="192.168.1.100", name=None, group=config.sonos_group)
        mock_nfc_class.assert_called_once_with(read_timeout_seconds=0.25)
        assert reader == mock_nfc_instance
        assert handle_tag_event is not None

    @patch("jukebox.di_container.SonosPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_sonos_name(self, mock_library, mock_current_tag, mock_reader, mock_player):
        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="sonos",
            sonos_host=None,
            sonos_name="Living Room",
            sonos_group=None,
            reader_type="dryrun",
            pause_duration_seconds=50,
            pause_delay_seconds=3,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.25,
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_current_tag.assert_called_once_with("/test/current-tag.txt")
        mock_player.assert_called_once_with(host=None, name="Living Room", group=None)
        mock_reader.assert_called_once_with()
        assert reader == mock_reader.return_value
        assert handle_tag_event is not None

    @patch("jukebox.di_container.SonosPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_sonos_autodiscovery(self, mock_library, mock_current_tag, mock_reader, mock_player):
        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="sonos",
            sonos_host=None,
            sonos_name=None,
            sonos_group=None,
            reader_type="dryrun",
            pause_duration_seconds=50,
            pause_delay_seconds=3,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.25,
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_current_tag.assert_called_once_with("/test/current-tag.txt")
        mock_player.assert_called_once_with(host=None, name=None, group=None)
        mock_reader.assert_called_once_with()
        assert reader == mock_reader.return_value
        assert handle_tag_event is not None

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_dryrun(self, mock_library, mock_current_tag, mock_reader, mock_player):
        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="dryrun",
            sonos_name=None,
            sonos_group=None,
            reader_type="dryrun",
            pause_duration_seconds=100,
            pause_delay_seconds=5,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.1,
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_current_tag.assert_called_once_with("/test/current-tag.txt")
        mock_player.assert_called_once_with()
        mock_reader.assert_called_once_with()

        assert reader == mock_reader.return_value
        assert handle_tag_event is not None

    @patch("jukebox.di_container.DryrunPlayerAdapter")
    @patch("jukebox.di_container.DryrunReaderAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_passes_correct_parameters_to_determine_action(
        self, mock_library, mock_current_tag, mock_reader, mock_player
    ):
        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="dryrun",
            sonos_name=None,
            sonos_group=None,
            reader_type="dryrun",
            pause_duration_seconds=200,
            pause_delay_seconds=0.2,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.1,
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        assert reader == mock_reader.return_value
        assert handle_tag_event.determine_action.pause_delay == 0.2
        assert handle_tag_event.determine_action.max_pause_duration == 200
