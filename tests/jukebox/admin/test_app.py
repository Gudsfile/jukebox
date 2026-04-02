from unittest.mock import ANY, MagicMock

import pytest
from typer.testing import CliRunner

from discstore.commands import (
    CliAddCommand,
    CliEditCommand,
    CliGetCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    CliSearchCommand,
    InteractiveCliCommand,
)
from jukebox.admin.app import app
from jukebox.admin.commands import (
    ApiCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    SonosListCommand,
    UiCommand,
)

runner = CliRunner()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        set_logger = mocker.patch("jukebox.admin.app.set_logger")
        build_admin_services = mocker.patch("jukebox.admin.app.build_admin_services")
        build_settings_service = mocker.patch("jukebox.admin.app.build_settings_service")
        execute_settings_command = mocker.patch("jukebox.admin.app.execute_settings_command")
        execute_sonos_command = mocker.patch("jukebox.admin.app.execute_sonos_command")
        execute_server_command = mocker.patch("jukebox.admin.app.execute_server_command")
        execute_library_command = mocker.patch("jukebox.admin.app.execute_library_command")
        build_api_app = mocker.patch("jukebox.admin.app.build_admin_api_app")
        build_ui_app = mocker.patch("jukebox.admin.app.build_admin_ui_app")
        build_cli_controller = mocker.patch("jukebox.admin.app.build_cli_controller")
        build_interactive_cli_controller = mocker.patch("jukebox.admin.app.build_interactive_cli_controller")

    return Mocks()


@pytest.mark.parametrize(
    ("args", "expected_command", "executor_name"),
    [
        (["settings", "show"], SettingsShowCommand(type="settings_show", effective=False), "execute_settings_command"),
        (
            ["settings", "show", "--effective"],
            SettingsShowCommand(type="settings_show", effective=True),
            "execute_settings_command",
        ),
        (
            ["settings", "show", "--json"],
            SettingsShowCommand(type="settings_show", effective=False, json_output=True),
            "execute_settings_command",
        ),
        (
            ["settings", "set", "admin.api.port", "9000"],
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
            "execute_settings_command",
        ),
        (
            ["settings", "reset", "admin.ui.port", "--json"],
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port", json_output=True),
            "execute_settings_command",
        ),
        (["sonos", "list"], SonosListCommand(type="sonos_list"), "execute_sonos_command"),
        (["api", "--port", "9000"], ApiCommand(type="api", port=9000), "execute_server_command"),
        (["ui", "--port", "9100"], UiCommand(type="ui", port=9100), "execute_server_command"),
    ],
)
def test_jukebox_admin_routes_admin_commands_by_category(app_mocks, args, expected_command, executor_name):
    services = MagicMock(settings=MagicMock(), sonos=MagicMock())
    app_mocks.build_admin_services.return_value = services

    result = runner.invoke(app, ["--library", "/custom/library.json", "--verbose", *args])

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox-admin", True)
    app_mocks.build_admin_services.assert_called_once_with(
        library="/custom/library.json",
        command=expected_command,
        logger_warning=ANY,
    )
    executor = getattr(app_mocks, executor_name)
    assert executor.call_count == 1

    if executor_name == "execute_settings_command":
        executor.assert_called_once_with(
            command=expected_command,
            settings_service=services.settings,
            source_command="jukebox-admin",
        )
        app_mocks.execute_sonos_command.assert_not_called()
        app_mocks.execute_server_command.assert_not_called()
    elif executor_name == "execute_sonos_command":
        executor.assert_called_once_with(command=expected_command, sonos_service=services.sonos)
        app_mocks.execute_settings_command.assert_not_called()
        app_mocks.execute_server_command.assert_not_called()
    else:
        executor.assert_called_once_with(
            verbose=True,
            command=expected_command,
            services=services,
            build_api_app=app_mocks.build_api_app,
            build_ui_app=app_mocks.build_ui_app,
            source_command="jukebox-admin",
        )
        app_mocks.execute_settings_command.assert_not_called()
        app_mocks.execute_sonos_command.assert_not_called()


def test_jukebox_admin_version_flag(app_mocks, mocker):
    mocker.patch("jukebox.admin.app.get_package_version", return_value="1.2.3")

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "jukebox-admin 1.2.3" in result.output
    app_mocks.set_logger.assert_not_called()
    app_mocks.build_admin_services.assert_not_called()
    app_mocks.execute_settings_command.assert_not_called()


def test_jukebox_admin_renders_friendly_settings_errors(app_mocks):
    app_mocks.build_admin_services.side_effect = ValueError("boom")

    result = runner.invoke(app, ["settings", "show"])

    assert result.exit_code == 1
    assert "Unexpected error. Re-run with `--verbose` for details." in result.output


def test_jukebox_admin_preserves_ui_startup_runtime_errors(app_mocks):
    services = MagicMock(settings=MagicMock(), sonos=MagicMock())
    app_mocks.build_admin_services.return_value = services
    app_mocks.execute_server_command.side_effect = RuntimeError("The `ui_controller` module requires Python 3.10+.")

    result = runner.invoke(app, ["ui"])

    assert result.exit_code == 1
    assert "The `ui_controller` module requires Python 3.10+." in result.output
    assert "Unexpected error. Re-run with `--verbose` for details." not in result.output


def test_jukebox_admin_preserves_library_validation_errors(app_mocks):
    settings_service = MagicMock()
    app_mocks.build_settings_service.return_value = settings_service
    app_mocks.execute_library_command.side_effect = ValueError("No current tag is available.")

    result = runner.invoke(app, ["library", "get", "--from-current"])

    assert result.exit_code == 1
    assert "No current tag is available." in result.output
    assert "Unexpected error. Re-run with `--verbose` for details." not in result.output


def test_jukebox_admin_preserves_os_errors(app_mocks):
    services = MagicMock(settings=MagicMock(), sonos=MagicMock())
    app_mocks.build_admin_services.return_value = services
    app_mocks.execute_settings_command.side_effect = PermissionError(
        "[Errno 13] Permission denied: '/tmp/settings.json'"
    )

    result = runner.invoke(app, ["settings", "show"])

    assert result.exit_code == 1
    assert "[Errno 13] Permission denied: '/tmp/settings.json'" in result.output
    assert "Unexpected error. Re-run with `--verbose` for details." not in result.output


@pytest.mark.parametrize(
    ("args", "expected_command"),
    [
        (
            ["library", "add", "tag-123", "--uri", "/music/song.mp3", "--track", "Song"],
            CliAddCommand(type="add", tag="tag-123", uri="/music/song.mp3", track="Song"),
        ),
        (
            ["library", "list", "line"],
            CliListCommand(type="list", mode=CliListCommandModes.line),
        ),
        (
            ["library", "remove", "--from-current"],
            CliRemoveCommand(type="remove", use_current_tag=True),
        ),
        (
            ["library", "edit", "tag-123", "--artist", "Updated Artist"],
            CliEditCommand(type="edit", tag="tag-123", artist="Updated Artist"),
        ),
        (
            ["library", "get", "--from-current"],
            CliGetCommand(type="get", use_current_tag=True),
        ),
        (
            ["library", "search", "beatles"],
            CliSearchCommand(type="search", query="beatles"),
        ),
        (
            ["library", "interactive"],
            InteractiveCliCommand(type="interactive"),
        ),
    ],
)
def test_jukebox_admin_routes_library_commands_to_shared_handler(app_mocks, args, expected_command):
    settings_service = MagicMock()
    app_mocks.build_settings_service.return_value = settings_service

    result = runner.invoke(app, ["--library", "/custom/library.json", "--verbose", *args])

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox-admin", True)
    app_mocks.build_settings_service.assert_called_once()
    build_kwargs = app_mocks.build_settings_service.call_args.kwargs
    assert build_kwargs["library"] == "/custom/library.json"
    assert build_kwargs["command"] == expected_command
    app_mocks.execute_library_command.assert_called_once_with(
        verbose=True,
        command=expected_command,
        settings_service=settings_service,
        build_cli_controller=app_mocks.build_cli_controller,
        build_interactive_cli_controller=app_mocks.build_interactive_cli_controller,
    )
    app_mocks.execute_settings_command.assert_not_called()
    app_mocks.execute_sonos_command.assert_not_called()
    app_mocks.execute_server_command.assert_not_called()
