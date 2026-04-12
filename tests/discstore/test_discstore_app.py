from unittest.mock import ANY, MagicMock

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
        build_admin_services = mocker.patch("discstore.app.build_admin_services")
        build_settings_service = mocker.patch("discstore.app._build_settings_service")
        execute_settings_command = mocker.patch("discstore.app.execute_settings_command")
        execute_server_command = mocker.patch("discstore.app.execute_server_command")
        execute_library_command = mocker.patch("discstore.app.execute_library_command")
        build_api_app = mocker.patch("discstore.app.build_admin_api_app")
        build_ui_app = mocker.patch("discstore.app.build_admin_ui_app")
        build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
        build_cli = mocker.patch("discstore.app.build_cli_controller")

    return Mocks()


@pytest.mark.parametrize(
    ("command", "executor_name"),
    [
        (ApiCommand(type="api", port=1234), "execute_server_command"),
        (UiCommand(type="ui", port=2345), "execute_server_command"),
        (SettingsShowCommand(type="settings_show", effective=False), "execute_settings_command"),
        (SettingsShowCommand(type="settings_show", effective=True), "execute_settings_command"),
        (
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
            "execute_settings_command",
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.playback.pause_duration_seconds",
                value="600",
            ),
            "execute_settings_command",
        ),
        (SettingsResetCommand(type="settings_reset", dotted_path="admin"), "execute_settings_command"),
    ],
)
def test_main_delegates_admin_commands_by_category(app_mocks, command, executor_name):
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=command)
    services = MagicMock(settings=MagicMock(), sonos=MagicMock())
    app_mocks.parse_config.return_value = config
    app_mocks.build_admin_services.return_value = services

    app.main()

    app_mocks.parse_config.assert_called_once_with()
    app_mocks.set_logger.assert_called_once_with("discstore", True)
    app_mocks.build_admin_services.assert_called_once_with(
        library="fake_library_path",
        command=command,
        logger_warning=ANY,
    )

    if executor_name == "execute_settings_command":
        app_mocks.execute_settings_command.assert_called_once_with(
            command=command,
            settings_service=services.settings,
            source_command="discstore",
            library="fake_library_path",
        )
        app_mocks.execute_server_command.assert_not_called()
    else:
        app_mocks.execute_server_command.assert_called_once_with(
            verbose=True,
            command=command,
            services=services,
            build_api_app=app_mocks.build_api_app,
            build_ui_app=app_mocks.build_ui_app,
            source_command="discstore",
        )
        app_mocks.execute_settings_command.assert_not_called()

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
    app_mocks.execute_settings_command.assert_not_called()
    app_mocks.execute_server_command.assert_not_called()


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


def test_main_exits_on_settings_error(app_mocks, capsys):
    config = DiscStoreConfig(command=SettingsShowCommand(type="settings_show"))
    app_mocks.parse_config.return_value = config
    app_mocks.build_admin_services.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert err.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == "broken settings"


def test_main_exits_on_settings_error_from_library_command(app_mocks, capsys):
    config = DiscStoreConfig(command=CliSearchCommand(type="search", query="dummy"))
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.execute_library_command.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert err.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == "broken settings"


def test_main_preserves_library_validation_errors(app_mocks, capsys):
    config = DiscStoreConfig(command=CliGetCommand(type="get", use_current_tag=True))
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.execute_library_command.side_effect = ValueError("No current tag is available.")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert err.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == "No current tag is available."


def test_main_preserves_admin_runtime_errors(app_mocks, capsys):
    config = DiscStoreConfig(command=UiCommand(type="ui"))
    services = MagicMock(settings=MagicMock(), sonos=MagicMock())
    app_mocks.parse_config.return_value = config
    app_mocks.build_admin_services.return_value = services
    app_mocks.execute_server_command.side_effect = RuntimeError("The `ui_controller` module requires Python 3.10+.")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert err.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == "The `ui_controller` module requires Python 3.10+."


def test_main_preserves_os_errors_from_library_commands(app_mocks, capsys):
    config = DiscStoreConfig(command=CliAddCommand(type="add", tag="dummy_tag", uri="dummy_uri"))
    settings_service = MagicMock()
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.execute_library_command.side_effect = PermissionError("[Errno 13] Permission denied: '/tmp/library.json'")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert err.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == "[Errno 13] Permission denied: '/tmp/library.json'"
