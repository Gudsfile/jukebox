import json
from importlib import import_module
from typing import Callable, Protocol

from jukebox.settings.service_protocols import ReadOnlySettingsService, SettingsService
from jukebox.shared.dependency_messages import optional_extra_dependency_message

from .commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand


class AppController(Protocol):
    app: object


def _load_uvicorn(command_name: str, extra_name: str, source_command: str):
    try:
        return import_module("uvicorn")
    except ModuleNotFoundError as err:
        if err.name not in (None, "uvicorn"):
            raise
        raise SystemExit(
            optional_extra_dependency_message(
                subject=f"`{source_command} {command_name}`",
                extra_name=extra_name,
                source_command=f"{source_command} {command_name}",
            )
        ) from err


def execute_admin_command(
    verbose: bool,
    command: object,
    settings_service: SettingsService,
    build_api_app: Callable[[str, SettingsService], AppController],
    build_ui_app: Callable[[str, ReadOnlySettingsService], AppController],
    source_command: str,
    print_fn: Callable[[str], None] = print,
) -> None:
    if isinstance(command, SettingsShowCommand):
        payload = (
            settings_service.get_effective_settings_view()
            if command.effective
            else settings_service.get_persisted_settings_view()
        )
        print_fn(json.dumps(payload, indent=2))
        return

    if isinstance(command, SettingsSetCommand):
        payload = settings_service.set_persisted_value(command.dotted_path, command.value)
        print_fn(json.dumps(payload, indent=2))
        return

    if isinstance(command, SettingsResetCommand):
        payload = settings_service.reset_persisted_value(command.dotted_path)
        print_fn(json.dumps(payload, indent=2))
        return

    runtime_config = settings_service.resolve_admin_runtime(verbose=verbose)

    if isinstance(command, ApiCommand):
        uvicorn = _load_uvicorn("api", "api", source_command)
        api = build_api_app(runtime_config.library_path, settings_service)
        uvicorn.run(api.app, host="0.0.0.0", port=runtime_config.api_port)
        return

    if isinstance(command, UiCommand):
        uvicorn = _load_uvicorn("ui", "ui", source_command)
        ui = build_ui_app(runtime_config.library_path, settings_service)
        uvicorn.run(ui.app, host="0.0.0.0", port=runtime_config.ui_port)
        return

    raise TypeError("Unsupported admin command")
