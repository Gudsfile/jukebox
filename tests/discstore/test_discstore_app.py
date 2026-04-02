from unittest.mock import MagicMock

import pytest

from discstore import app
from discstore.adapters.inbound.config import (
    CliAddCommand,
    CliEditCommand,
    CliGetCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    CliSearchCommand,
    DiscStoreConfig,
)
from discstore.commands import InteractiveCliCommand
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        parse_config = mocker.patch("discstore.app.parse_config")
        set_logger = mocker.patch("discstore.app.set_logger")
        build_settings_service = mocker.patch("discstore.app._build_settings_service")
        execute_admin_command = mocker.patch("discstore.app.execute_admin_command")
        execute_library_command = mocker.patch("discstore.app.execute_library_command")
        build_api_app = mocker.patch("discstore.app.build_admin_api_app")
        build_ui_app = mocker.patch("discstore.app.build_admin_ui_app")
        build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
        build_cli = mocker.patch("discstore.app.build_cli_controller")

    return Mocks()


@pytest.mark.parametrize(
    "command",
    [
        ApiCommand(type="api", port=1234),
        UiCommand(type="ui", port=2345),
        SettingsShowCommand(type="settings_show", effective=False),
        SettingsShowCommand(type="settings_show", effective=True),
        SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.playback.pause_duration_seconds",
            value="600",
        ),
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.reader.type",
            value="nfc",
        ),
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.reader.nfc.read_timeout_seconds",
            value="0.2",
        ),
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.player.type",
            value="sonos",
        ),
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.player.sonos.selected_group",
            value='{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"}]}',
        ),
        SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
        SettingsResetCommand(type="settings_reset", dotted_path="jukebox.runtime.loop_interval_seconds"),
        SettingsResetCommand(type="settings_reset", dotted_path="jukebox.reader.nfc.read_timeout_seconds"),
        SettingsResetCommand(type="settings_reset", dotted_path="jukebox.player.sonos.selected_group"),
        SettingsResetCommand(type="settings_reset", dotted_path="admin"),
    ],
)
def test_main_delegates_admin_commands_to_shared_handler(app_mocks, command):
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=command)
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service

    app.main()

    app_mocks.parse_config.assert_called_once_with()
    app_mocks.set_logger.assert_called_once_with("discstore", True)
    app_mocks.build_settings_service.assert_called_once_with(config)
    app_mocks.execute_admin_command.assert_called_once_with(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=app_mocks.build_api_app,
        build_ui_app=app_mocks.build_ui_app,
        source_command="discstore",
    )
    app_mocks.build_interactive.assert_not_called()
    app_mocks.build_cli.assert_not_called()


@pytest.mark.parametrize(
    "cli_command",
    [
        InteractiveCliCommand(type="interactive"),
        CliAddCommand(type="add", tag="dummy_tag", uri="dummy_uri"),
        CliRemoveCommand(type="remove", tag="dummy_tag"),
        CliListCommand(type="list", mode=CliListCommandModes.table),
        CliEditCommand(type="edit", tag="dummy_tag", uri="dummy_uri"),
        CliGetCommand(type="get", tag="dummy_tag"),
        CliSearchCommand(type="search", query="dummy"),
    ],
)
def test_main_delegates_library_commands_to_shared_handler(app_mocks, cli_command):
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=cli_command)
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service

    app.main()

    app_mocks.set_logger.assert_called_once_with("discstore", True)
    app_mocks.build_settings_service.assert_called_once_with(config)
    app_mocks.execute_library_command.assert_called_once_with(
        verbose=True,
        command=cli_command,
        settings_service=settings_service,
        build_cli_controller=app_mocks.build_cli,
        build_interactive_cli_controller=app_mocks.build_interactive,
    )
    app_mocks.execute_admin_command.assert_not_called()


def test_build_settings_service_reads_persisted_admin_ports(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        '{"schema_version": 1, "admin": {"api": {"port": 8100}, "ui": {"port": 8200}}}',
        encoding="utf-8",
    )
    mocker.patch(
        "jukebox.admin.di_container.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path))
    )

    settings_service = app._build_settings_service(DiscStoreConfig(command=ApiCommand(type="api")))
    runtime_config = settings_service.resolve_admin_runtime()

    assert runtime_config.api_port == 8100
    assert runtime_config.ui_port == 8200


def test_main_exits_on_settings_error(app_mocks):
    config = DiscStoreConfig(command=SettingsShowCommand(type="settings_show"))
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert str(err.value) == "broken settings"


def test_main_exits_on_settings_error_from_library_command(app_mocks):
    config = DiscStoreConfig(command=CliSearchCommand(type="search", query="dummy"))
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.execute_library_command.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert str(err.value) == "broken settings"
