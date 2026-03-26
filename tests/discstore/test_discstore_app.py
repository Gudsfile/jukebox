import json
from unittest.mock import MagicMock

import pytest

from discstore import app
from discstore.adapters.inbound.config import (
    ApiCommand,
    CliAddCommand,
    CliEditCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    DiscStoreConfig,
    InteractiveCliCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    UiCommand,
)
from jukebox.settings.entities import ResolvedAdminRuntimeConfig
from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository


def assert_app_mocks_calls(app_mocks, expected_calls: dict):
    all_mock_names = [
        "parse_config",
        "set_logger",
        "build_settings_service",
        "build_api_app",
        "build_interactive",
        "build_cli",
        "build_ui_app",
        "print",
    ]

    for name in all_mock_names:
        mock_obj = getattr(app_mocks, name)
        if name in expected_calls:
            expected_args = expected_calls[name]
            mock_obj.assert_called_once_with(*expected_args)
        else:
            mock_obj.assert_not_called()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        parse_config = mocker.patch("discstore.app.parse_config")
        set_logger = mocker.patch("discstore.app.set_logger")
        build_settings_service = mocker.patch("discstore.app._build_settings_service")
        build_api_app = mocker.patch("discstore.app.build_api_app")
        build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
        build_cli = mocker.patch("discstore.app.build_cli_controller")
        build_ui_app = mocker.patch("discstore.app.build_ui_app")
        print = mocker.patch("builtins.print")

    return Mocks()


@pytest.mark.parametrize(
    ("command", "expected_builder", "expected_port"),
    [
        (ApiCommand(type="api", port=1234), "build_api_app", 7777),
        (UiCommand(type="ui", port=1234), "build_ui_app", 8888),
    ],
)
def test_main_starts_server_commands_with_resolved_runtime(mocker, app_mocks, command, expected_builder, expected_port):
    mock_uvicorn = mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})["uvicorn"]
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=command)
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=7777,
        ui_port=8888,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service
    fake_apps = {
        "build_api_app": MagicMock(),
        "build_ui_app": MagicMock(),
    }
    app_mocks.build_api_app.return_value = MagicMock(app=fake_apps["build_api_app"])
    app_mocks.build_ui_app.return_value = MagicMock(app=fake_apps["build_ui_app"])

    app.main()

    expected_calls = {
        "parse_config": (),
        "set_logger": ("discstore", True),
        "build_settings_service": (config,),
    }
    if expected_builder == "build_api_app":
        expected_calls["build_api_app"] = ("/resolved/library.json", settings_service)
    else:
        expected_calls["build_ui_app"] = ("/resolved/library.json", settings_service)

    assert_app_mocks_calls(app_mocks, expected_calls)
    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    mock_uvicorn.run.assert_called_once_with(fake_apps[expected_builder], host="0.0.0.0", port=expected_port)


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

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": ("discstore", True),
            "build_settings_service": (config,),
            "build_interactive": ("/resolved/library.json",),
        },
    )
    mock_interactive_cli.run.assert_called_once_with()


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

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": ("discstore", True),
            "build_settings_service": (config,),
            "build_cli": ("/resolved/library.json",),
        },
    )
    mock_standard_cli.run.assert_called_once_with(cli_command)


def test_main_prints_settings_show_payload(app_mocks):
    config = DiscStoreConfig(verbose=True, command=SettingsShowCommand(type="settings_show", effective=True))
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {"settings": {"admin": {"api": {"port": 8000}}}}
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service

    app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": ("discstore", True),
            "build_settings_service": (config,),
            "print": (json.dumps({"settings": {"admin": {"api": {"port": 8000}}}}, indent=2),),
        },
    )
    settings_service.get_effective_settings_view.assert_called_once_with()


@pytest.mark.parametrize(
    ("command", "service_method", "service_args"),
    [
        (
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
            "set_persisted_value",
            ("admin.api.port", "9000"),
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.playback.pause_duration_seconds",
                value="600",
            ),
            "set_persisted_value",
            ("jukebox.playback.pause_duration_seconds", "600"),
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
            "reset_persisted_value",
            ("admin.ui.port",),
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="jukebox.runtime.loop_interval_seconds"),
            "reset_persisted_value",
            ("jukebox.runtime.loop_interval_seconds",),
        ),
        (SettingsResetCommand(type="settings_reset", dotted_path="admin"), "reset_persisted_value", ("admin",)),
    ],
)
def test_main_prints_settings_write_payload(app_mocks, command, service_method, service_args):
    config = DiscStoreConfig(verbose=True, command=command)
    settings_service = MagicMock()
    getattr(settings_service, service_method).return_value = {"message": "Settings saved."}
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.return_value = settings_service

    app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": ("discstore", True),
            "build_settings_service": (config,),
            "print": (json.dumps({"message": "Settings saved."}, indent=2),),
        },
    )
    getattr(settings_service, service_method).assert_called_once_with(*service_args)


def test_build_settings_service_reads_persisted_admin_ports(tmp_path, mocker):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "admin": {"api": {"port": 8100}, "ui": {"port": 8200}},
            }
        ),
        encoding="utf-8",
    )
    mocker.patch("discstore.app.FileSettingsRepository", return_value=FileSettingsRepository(str(settings_path)))

    settings_service = app._build_settings_service(DiscStoreConfig(command=ApiCommand(type="api")))
    runtime_config = settings_service.resolve_admin_runtime()

    assert runtime_config.api_port == 8100
    assert runtime_config.ui_port == 8200


@pytest.mark.parametrize(
    ("command", "extra_name"),
    [
        (ApiCommand(type="api", port=1234), "api"),
        (UiCommand(type="ui", port=1234), "ui"),
    ],
)
def test_main_reports_missing_optional_server_dependencies(mocker, app_mocks, command, extra_name):
    config = DiscStoreConfig(library="fake_library_path", verbose=True, command=command)
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
    mocker.patch("discstore.app.import_module", side_effect=ModuleNotFoundError("No module named 'uvicorn'"))

    with pytest.raises(SystemExit) as err:
        app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": ("discstore", True),
            "build_settings_service": (config,),
        },
    )
    assert f"`discstore {extra_name}` requires the optional `{extra_name}` dependencies." in str(err.value)


def test_main_exits_on_settings_error(app_mocks):
    config = DiscStoreConfig(command=SettingsShowCommand(type="settings_show"))
    app_mocks.parse_config.return_value = config
    app_mocks.build_settings_service.side_effect = InvalidSettingsError("broken settings")

    with pytest.raises(SystemExit) as err:
        app.main()

    assert str(err.value) == "broken settings"
