import json
from unittest.mock import MagicMock

import pytest

from jukebox.admin.command_handlers import execute_admin_command
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from jukebox.settings.entities import ResolvedAdminRuntimeConfig
from jukebox.shared.dependency_messages import optional_extra_dependency_message


def test_execute_admin_command_prints_persisted_settings():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    print_fn = MagicMock()

    execute_admin_command(
        verbose=False,
        command=SettingsShowCommand(type="settings_show"),
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="jukebox-admin",
        print_fn=print_fn,
    )

    settings_service.get_persisted_settings_view.assert_called_once_with()
    print_fn.assert_called_once_with(json.dumps({"schema_version": 1}, indent=2))


@pytest.mark.parametrize(
    ("command", "service_method", "service_args", "payload"),
    [
        (
            SettingsShowCommand(type="settings_show", effective=True),
            "get_effective_settings_view",
            (),
            {"settings": {"admin": {"api": {"port": 8000}}}},
        ),
        (
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
            "set_persisted_value",
            ("admin.api.port", "9000"),
            {"persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}},
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
            "reset_persisted_value",
            ("admin.ui.port",),
            {"persisted": {"schema_version": 1, "admin": {}}},
        ),
    ],
)
def test_execute_admin_command_uses_shared_settings_operations(command, service_method, service_args, payload):
    settings_service = MagicMock()
    getattr(settings_service, service_method).return_value = payload
    print_fn = MagicMock()

    execute_admin_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="discstore",
        print_fn=print_fn,
    )

    getattr(settings_service, service_method).assert_called_once_with(*service_args)
    print_fn.assert_called_once_with(json.dumps(payload, indent=2))


@pytest.mark.parametrize(
    ("command", "builder_name", "expected_port"),
    [
        (ApiCommand(type="api", port=1111), "build_api_app", 7777),
        (UiCommand(type="ui", port=2222), "build_ui_app", 8888),
    ],
)
def test_execute_admin_command_starts_server_with_resolved_runtime(mocker, command, builder_name, expected_port):
    mock_uvicorn = mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})["uvicorn"]
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=7777,
        ui_port=8888,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    fake_app = MagicMock(app=MagicMock(name=f"{builder_name}_app"))
    build_api_app = MagicMock(return_value=fake_app)
    build_ui_app = MagicMock(return_value=fake_app)

    execute_admin_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=build_api_app,
        build_ui_app=build_ui_app,
        source_command="jukebox-admin",
    )

    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    if builder_name == "build_api_app":
        build_api_app.assert_called_once_with("/resolved/library.json", settings_service)
        build_ui_app.assert_not_called()
    else:
        build_ui_app.assert_called_once_with("/resolved/library.json", settings_service)
        build_api_app.assert_not_called()
    mock_uvicorn.run.assert_called_once_with(fake_app.app, host="0.0.0.0", port=expected_port)


@pytest.mark.parametrize(
    ("command", "extra_name"),
    [
        (ApiCommand(type="api", port=1234), "api"),
        (UiCommand(type="ui", port=1234), "ui"),
    ],
)
def test_execute_admin_command_reports_missing_optional_dependencies(mocker, command, extra_name):
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
    mocker.patch(
        "jukebox.admin.command_handlers.import_module",
        side_effect=ModuleNotFoundError("No module named 'uvicorn'"),
    )

    with pytest.raises(SystemExit) as err:
        execute_admin_command(
            verbose=False,
            command=command,
            settings_service=settings_service,
            build_api_app=MagicMock(),
            build_ui_app=MagicMock(),
            source_command="jukebox-admin",
        )

    assert f"`jukebox-admin {extra_name}` requires the optional `{extra_name}` dependencies." in str(err.value)


@pytest.mark.parametrize(
    ("command", "extra_name", "builder_name"),
    [
        (ApiCommand(type="api", port=1234), "api", "build_api_app"),
        (UiCommand(type="ui", port=1234), "ui", "build_ui_app"),
    ],
)
def test_execute_admin_command_rewrites_controller_dependency_failures(mocker, command, extra_name, builder_name):
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})
    build_api_app = MagicMock()
    build_ui_app = MagicMock()
    target_builder = build_api_app if builder_name == "build_api_app" else build_ui_app
    target_builder.side_effect = ModuleNotFoundError(
        optional_extra_dependency_message(
            subject="The legacy controller module",
            extra_name=extra_name,
            source_command=f"discstore {extra_name}",
        )
    )

    with pytest.raises(SystemExit) as err:
        execute_admin_command(
            verbose=False,
            command=command,
            settings_service=settings_service,
            build_api_app=build_api_app,
            build_ui_app=build_ui_app,
            source_command="jukebox-admin",
        )

    assert str(err.value) == optional_extra_dependency_message(
        subject=f"`jukebox-admin {extra_name}`",
        extra_name=extra_name,
        source_command=f"jukebox-admin {extra_name}",
    )
