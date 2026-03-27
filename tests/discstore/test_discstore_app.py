from unittest.mock import MagicMock

import pytest

from discstore import app
from discstore.adapters.inbound.config import (
    CliAddCommand,
    CliEditCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    DiscStoreConfig,
    InteractiveCliCommand,
)
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from jukebox.settings.entities import ResolvedAdminRuntimeConfig
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        parse_config = mocker.patch("discstore.app.parse_config")
        set_logger = mocker.patch("discstore.app.set_logger")
        build_settings_service = mocker.patch("discstore.app._build_settings_service")
        execute_admin_command = mocker.patch("discstore.app.execute_admin_command")
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
        SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
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


def test_main_starts_interactive_cli(app_mocks):
    config = DiscStoreConfig(
        library="fake_library_path", verbose=True, command=InteractiveCliCommand(type="interactive")
    )
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=8000,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    mock_interactive_cli = MagicMock()
    app_mocks.build_interactive.return_value = mock_interactive_cli

    app.main()

    app_mocks.set_logger.assert_called_once_with("discstore", True)
    app_mocks.build_settings_service.assert_called_once_with(config)
    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    app_mocks.build_interactive.assert_called_once_with("/resolved/library.json")
    mock_interactive_cli.run.assert_called_once_with()
    app_mocks.execute_admin_command.assert_not_called()
    app_mocks.build_cli.assert_not_called()


@pytest.mark.parametrize(
    "cli_command",
    [
        CliAddCommand(type="add", tag="dummy_tag", uri="dummy_uri"),
        CliRemoveCommand(type="remove", tag="dummy_tag"),
        CliListCommand(type="list", mode=CliListCommandModes.table),
        CliEditCommand(type="edit", tag="dummy_tag", uri="dummy_uri"),
    ],
)
def test_main_starts_standard_cli(app_mocks, cli_command):
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=cli_command)
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=8000,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    mock_standard_cli = MagicMock()
    app_mocks.build_cli.return_value = mock_standard_cli

    app.main()

    app_mocks.set_logger.assert_called_once_with("discstore", True)
    app_mocks.build_settings_service.assert_called_once_with(config)
    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    app_mocks.build_cli.assert_called_once_with("/resolved/library.json")
    mock_standard_cli.run.assert_called_once_with(cli_command)
    app_mocks.execute_admin_command.assert_not_called()
    app_mocks.build_interactive.assert_not_called()


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
