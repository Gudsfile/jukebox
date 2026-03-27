from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from jukebox.admin.app import app
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand

runner = CliRunner()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        set_logger = mocker.patch("jukebox.admin.app.set_logger")
        build_settings_service = mocker.patch("jukebox.admin.app.build_settings_service")
        execute_admin_command = mocker.patch("jukebox.admin.app.execute_admin_command")
        build_api_app = mocker.patch("jukebox.admin.app.build_admin_api_app")
        build_ui_app = mocker.patch("jukebox.admin.app.build_admin_ui_app")

    return Mocks()


@pytest.mark.parametrize(
    ("args", "expected_command"),
    [
        (["settings", "show"], SettingsShowCommand(type="settings_show", effective=False)),
        (["settings", "show", "--effective"], SettingsShowCommand(type="settings_show", effective=True)),
        (
            ["settings", "set", "admin.api.port", "9000"],
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
        ),
        (
            ["settings", "reset", "admin.ui.port"],
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
        ),
        (["api", "--port", "9000"], ApiCommand(type="api", port=9000)),
        (["ui", "--port", "9100"], UiCommand(type="ui", port=9100)),
    ],
)
def test_jukebox_admin_routes_commands_to_shared_handler(app_mocks, args, expected_command):
    settings_service = MagicMock()
    app_mocks.build_settings_service.return_value = settings_service

    result = runner.invoke(app, ["--library", "/custom/library.json", "--verbose", *args])

    assert result.exit_code == 0
    app_mocks.set_logger.assert_called_once_with("jukebox-admin", True)
    app_mocks.build_settings_service.assert_called_once()
    build_kwargs = app_mocks.build_settings_service.call_args.kwargs
    assert build_kwargs["library"] == "/custom/library.json"
    assert build_kwargs["command"] == expected_command
    app_mocks.execute_admin_command.assert_called_once_with(
        verbose=True,
        command=expected_command,
        settings_service=settings_service,
        build_api_app=app_mocks.build_api_app,
        build_ui_app=app_mocks.build_ui_app,
        source_command="jukebox-admin",
    )


def test_jukebox_admin_version_flag(app_mocks, mocker):
    mocker.patch("jukebox.admin.app.get_package_version", return_value="1.2.3")

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "jukebox-admin 1.2.3" in result.output
    app_mocks.set_logger.assert_not_called()
    app_mocks.build_settings_service.assert_not_called()
    app_mocks.execute_admin_command.assert_not_called()
