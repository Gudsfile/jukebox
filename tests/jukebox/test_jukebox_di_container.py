from unittest.mock import MagicMock, patch

from jukebox.di_container import build_jukebox, build_settings_service
from jukebox.pn532.profiles import SpiConnectionParams
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.shared.config_utils import get_current_tag_path
from tests.jukebox.settings._helpers import (
    StubSonosService,
    build_resolved_sonos_group_runtime,
    resolve_jukebox_runtime,
)


def test_get_current_tag_path_derives_path_beside_library(tmp_path):
    library_path = tmp_path / "nested" / "library.json"

    assert get_current_tag_path(str(library_path)) == str(tmp_path / "nested" / "current-tag.txt")


class TestBuildJukebox:
    @patch("jukebox.di_container.SonosPlayerAdapter")
    @patch("jukebox.di_container.TextCurrentTagAdapter")
    @patch("jukebox.di_container.JsonLibraryAdapter")
    def test_build_jukebox_with_sonos_and_pn532(self, mock_library, mock_current_tag, mock_player, mocker):
        mock_pn532_instance = MagicMock()
        mock_pn532_class = MagicMock(return_value=mock_pn532_instance)
        mocker.patch.dict(
            "sys.modules",
            {"jukebox.adapters.outbound.readers.pn532_reader_adapter": MagicMock(Pn532ReaderAdapter=mock_pn532_class)},
        )

        config = ResolvedJukeboxRuntimeConfig(
            library_path="/test/library.json",
            player_type="sonos",
            sonos_host="192.168.1.100",
            sonos_name=None,
            sonos_group=build_resolved_sonos_group_runtime(
                speakers=[("speaker-1", "Living Room", "192.168.1.100", "household-1")]
            ),
            reader_type="pn532",
            pause_duration_seconds=50,
            pause_delay_seconds=3,
            loop_interval_seconds=0.1,
            pn532_read_timeout_seconds=0.25,
            pn532_board_profile="waveshare_hat",
            pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        mock_library.assert_called_once_with("/test/library.json")
        mock_current_tag.assert_called_once_with("/test/current-tag.txt")
        mock_player.assert_called_once_with(host="192.168.1.100", name=None, group=config.sonos_group)
        mock_pn532_class.assert_called_once_with(
            read_timeout_seconds=0.25,
            spi_reset=20,
            spi_cs=4,
            spi_irq=None,
        )
        assert reader == mock_pn532_instance
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
            pn532_read_timeout_seconds=0.25,
            pn532_board_profile="waveshare_hat",
            pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
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
            pn532_read_timeout_seconds=0.25,
            pn532_board_profile="waveshare_hat",
            pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
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
            pn532_read_timeout_seconds=0.1,
            pn532_board_profile="waveshare_hat",
            pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
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
            pn532_read_timeout_seconds=0.1,
            pn532_board_profile="waveshare_hat",
            pn532_connection=SpiConnectionParams(reset=20, cs=4, irq=None),
            verbose=False,
        )

        reader, handle_tag_event = build_jukebox(config)

        assert reader == mock_reader.return_value
        assert handle_tag_event.determine_action.pause_delay == 0.2
        assert handle_tag_event.determine_action.max_pause_duration == 200


class TestBuildSettingService:
    def test_build_settings_service_maps_sonos_name_override(self):
        service = build_settings_service(player="sonos", sonos_name="Living Room")

        assert isinstance(service.repository, FileSettingsRepository)
        assert service.cli_overrides == {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None},
                }
            }
        }

    def test_build_settings_service_maps_sonos_host_override(self):
        service = build_settings_service(player="sonos", sonos_host="192.168.1.20")

        assert service.cli_overrides == {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {"manual_host": "192.168.1.20", "manual_name": None, "selected_group": None},
                }
            }
        }

    def test_build_settings_service_reads_persisted_reader_and_timing_settings(self, tmp_path, mocker):
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(
            '{"schema_version": 1, "jukebox": {"reader": {"type": "pn532", "pn532": {"read_timeout_seconds": 0.2}}, "playback": {"pause_duration_seconds": 600, "pause_delay_seconds": 0.3}, "runtime": {"loop_interval_seconds": 0.2}}}',
            encoding="utf-8",
        )
        mocker.patch(
            "jukebox.di_container.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path))
        )

        settings_service = build_settings_service()
        runtime_config = resolve_jukebox_runtime(settings_service)

        assert runtime_config.reader_type == "pn532"
        assert runtime_config.pn532_read_timeout_seconds == 0.2
        assert runtime_config.pause_duration_seconds == 600
        assert runtime_config.pause_delay_seconds == 0.3
        assert runtime_config.loop_interval_seconds == 0.2

    def test_build_settings_service_maps_pn532_overrides(self):
        service = build_settings_service(pn532_spi_reset=25, pn532_spi_cs=10, pn532_spi_irq=24)

        assert service.cli_overrides == {
            "jukebox": {
                "reader": {
                    "pn532": {
                        "spi": {"reset": 25, "cs": 10, "irq": 24},
                    }
                }
            }
        }

    def test_build_settings_service_reads_persisted_selected_group_target(self, tmp_path, mocker):
        settings_path = tmp_path / "settings.json"
        settings_path.write_text(
            '{"schema_version": 1, "jukebox": {"player": {"type": "sonos", "sonos": {"selected_group": {"coordinator_uid": "speaker-2", "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}]}}}}}',
            encoding="utf-8",
        )
        mocker.patch(
            "jukebox.di_container.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path))
        )

        settings_service = build_settings_service()
        runtime_config = resolve_jukebox_runtime(
            settings_service,
            StubSonosService(
                resolved_group=build_resolved_sonos_group_runtime(
                    coordinator_uid="speaker-2",
                    speakers=[
                        ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
                        ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
                    ],
                ),
            ),
        )

        assert runtime_config.player_type == "sonos"
        assert runtime_config.sonos_host == "192.168.1.40"
        assert runtime_config.sonos_name is None
        assert runtime_config.sonos_group is not None
