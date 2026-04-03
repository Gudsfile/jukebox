import sys
from importlib import import_module
from typing import Callable, Optional, Protocol

from jukebox.settings.service_protocols import ReadOnlySettingsService, SettingsService
from jukebox.shared.dependency_messages import optional_extra_dependency_message

from .cli_presentation import build_discstore_settings_deprecation_warning, render_settings_output
from .commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand


class AppController(Protocol):
    app: object


def _raise_optional_extra_error(command_name: str, extra_name: str, source_command: str, err: ModuleNotFoundError):
    raise SystemExit(
        optional_extra_dependency_message(
            subject=f"`{source_command} {command_name}`",
            extra_name=extra_name,
            source_command=f"{source_command} {command_name}",
        )
    ) from err


def _load_uvicorn(command_name: str, extra_name: str, source_command: str):
    try:
        return import_module("uvicorn")
    except ModuleNotFoundError as err:
        if err.name not in (None, "uvicorn"):
            raise
        _raise_optional_extra_error(command_name, extra_name, source_command, err)


def _build_server_app(
    build_app: Callable[[str, SettingsService], AppController],
    library_path: str,
    settings_service: SettingsService,
    command_name: str,
    extra_name: str,
    source_command: str,
):
    try:
        return build_app(library_path, settings_service)
    except ModuleNotFoundError as err:
        if err.name in {"fastapi", "fastui"} or "requires the optional" in str(err):
            _raise_optional_extra_error(command_name, extra_name, source_command, err)
        raise


def execute_admin_command(
    verbose: bool,
    command: object,
    settings_service: SettingsService,
    build_api_app: Callable[[str, SettingsService], AppController],
    build_ui_app: Callable[[str, ReadOnlySettingsService], AppController],
    source_command: str,
    library: Optional[str] = None,
    stdout_fn: Callable[[str], None] = print,
    stderr_fn: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> None:
    if source_command == "discstore" and isinstance(
        command,
        (SettingsShowCommand, SettingsSetCommand, SettingsResetCommand),
    ):
        stderr_fn(build_discstore_settings_deprecation_warning(command, library=library))

    if isinstance(command, SettingsShowCommand):
        payload = (
            settings_service.get_effective_settings_view()
            if command.effective
            else settings_service.get_persisted_settings_view()
        )
        stdout_fn(render_settings_output(command, payload))
        return

    if isinstance(command, SettingsSetCommand):
        payload = settings_service.set_persisted_value(command.dotted_path, command.value)
        stdout_fn(render_settings_output(command, payload))
        return

    if isinstance(command, SettingsResetCommand):
        payload = settings_service.reset_persisted_value(command.dotted_path)
        stdout_fn(render_settings_output(command, payload))
        return

    runtime_config = settings_service.resolve_admin_runtime(verbose=verbose)

    if isinstance(command, ApiCommand):
        uvicorn = _load_uvicorn("api", "api", source_command)
        api = _build_server_app(
            build_app=build_api_app,
            library_path=runtime_config.library_path,
            settings_service=settings_service,
            command_name="api",
            extra_name="api",
            source_command=source_command,
        )
        uvicorn.run(api.app, host="0.0.0.0", port=runtime_config.api_port)
        return

    if isinstance(command, UiCommand):
        uvicorn = _load_uvicorn("ui", "ui", source_command)
        ui = _build_server_app(
            build_app=build_ui_app,
            library_path=runtime_config.library_path,
            settings_service=settings_service,
            command_name="ui",
            extra_name="ui",
            source_command=source_command,
        )
        uvicorn.run(ui.app, host="0.0.0.0", port=runtime_config.ui_port)
        return

    raise TypeError("Unsupported admin command")
