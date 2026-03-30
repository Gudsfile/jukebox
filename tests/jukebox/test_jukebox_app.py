from unittest.mock import MagicMock

import pytest

from jukebox import app
from jukebox.adapters.inbound.config import JukeboxCliConfig
from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        parse_config = mocker.patch("jukebox.app.parse_config")
        set_logger = mocker.patch("jukebox.app.set_logger")
        build_settings_service = mocker.patch("jukebox.app._build_settings_service")
        build_jukebox = mocker.patch("jukebox.app.build_jukebox")
        controller_class = mocker.patch("jukebox.app.CLIController")

    return Mocks()


def test_main_uses_resolved_runtime_config(app_mocks):
    runtime_config = ResolvedJukeboxRuntimeConfig(
        library_path="/resolved/library.json",
        player_type="dryrun",
        reader_type="dryrun",
        pause_duration_seconds=100,
        pause_delay_seconds=1.0,
        loop_interval_seconds=0.5,
        nfc_read_timeout_seconds=0.1,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_jukebox_runtime.return_value = runtime_config
    app_mocks.parse_config.return_value = JukeboxCliConfig(verbose=True)
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.build_jukebox.return_value = (MagicMock(), MagicMock())

    app.main()

    app_mocks.set_logger.assert_called_once_with("jukebox", True)
    app_mocks.build_settings_service.assert_called_once_with(JukeboxCliConfig(verbose=True))
    settings_service.resolve_jukebox_runtime.assert_called_once_with(verbose=True)
    app_mocks.build_jukebox.assert_called_once_with(runtime_config)
    app_mocks.controller_class.assert_called_once()
    assert app_mocks.controller_class.call_args.kwargs["loop_interval_seconds"] == 0.5
    app_mocks.controller_class.return_value.run.assert_called_once_with()


def test_main_exits_on_settings_error(app_mocks):
    app_mocks.parse_config.return_value = JukeboxCliConfig()
    app_mocks.build_settings_service.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert str(err.value) == "broken settings"


def test_build_settings_service_maps_sonos_name_override():
    service = app._build_settings_service(JukeboxCliConfig(player="sonos", sonos_name="Living Room"))

    assert isinstance(service.repository, FileSettingsRepository)
    assert service.cli_overrides == {
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None},
            }
        }
    }


def test_build_settings_service_maps_sonos_host_override():
    service = app._build_settings_service(JukeboxCliConfig(player="sonos", sonos_host="192.168.1.20"))

    assert service.cli_overrides == {
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": "192.168.1.20", "manual_name": None, "selected_group": None},
            }
        }
    }


def test_build_settings_service_reads_persisted_reader_and_timing_settings(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"schema_version": 1, "jukebox": {"reader": {"type": "nfc", "nfc": {"read_timeout_seconds": 0.2}}, "playback": {"pause_duration_seconds": 600, "pause_delay_seconds": 0.3}, "runtime": {"loop_interval_seconds": 0.2}}}',
        encoding="utf-8",
    )
    mocker.patch("jukebox.app.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))

    settings_service = app._build_settings_service(JukeboxCliConfig())
    runtime_config = settings_service.resolve_jukebox_runtime()

    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.2
    assert runtime_config.pause_duration_seconds == 600
    assert runtime_config.pause_delay_seconds == 0.3
    assert runtime_config.loop_interval_seconds == 0.2


def test_build_settings_service_reads_persisted_selected_group_target(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"schema_version": 1, "jukebox": {"player": {"type": "sonos", "sonos": {"selected_group": {"coordinator_uid": "speaker-2", "members": [{"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"}, {"uid": "speaker-2", "name": "Living Room", "last_known_host": "192.168.1.40"}]}}}}}',
        encoding="utf-8",
    )
    mocker.patch("jukebox.app.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))

    settings_service = app._build_settings_service(JukeboxCliConfig())
    runtime_config = settings_service.resolve_jukebox_runtime()

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_name is None
