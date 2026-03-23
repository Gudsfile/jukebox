import json
import logging
from importlib import import_module

from discstore.adapters.inbound.config import (
    ApiCommand,
    DiscStoreConfig,
    InteractiveCliCommand,
    SettingsShowCommand,
    UiCommand,
    parse_config,
)
from discstore.di_container import build_api_app, build_cli_controller, build_interactive_cli_controller, build_ui_app
from jukebox.settings.errors import SettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsReadService, build_environment_settings_overrides
from jukebox.shared.dependency_messages import optional_extra_dependency_message
from jukebox.shared.logger import set_logger

LOGGER = logging.getLogger("discstore")


def _load_uvicorn(command_name: str, extra_name: str):
    try:
        return import_module("uvicorn")
    except ModuleNotFoundError as err:
        if err.name not in (None, "uvicorn"):
            raise
        raise SystemExit(
            optional_extra_dependency_message(
                subject=f"`discstore {command_name}`",
                extra_name=extra_name,
                source_command=f"discstore {command_name}",
            )
        ) from err


def _build_settings_service(config: DiscStoreConfig) -> SettingsReadService:
    cli_overrides = {}

    if config.library is not None:
        cli_overrides.setdefault("paths", {})["library_path"] = config.library

    if isinstance(config.command, ApiCommand) and config.command.port is not None:
        cli_overrides.setdefault("admin", {}).setdefault("api", {})["port"] = config.command.port

    if isinstance(config.command, UiCommand) and config.command.port is not None:
        cli_overrides.setdefault("admin", {}).setdefault("ui", {})["port"] = config.command.port

    return SettingsReadService(
        repository=FileSettingsRepository(),
        env_overrides=build_environment_settings_overrides(LOGGER.warning),
        cli_overrides=cli_overrides,
    )


def main():
    config = parse_config()
    set_logger("discstore", config.verbose)
    try:
        settings_service = _build_settings_service(config)
        if isinstance(config.command, SettingsShowCommand):
            payload = (
                settings_service.get_effective_settings_view()
                if config.command.effective
                else settings_service.get_persisted_settings_view()
            )
            print(json.dumps(payload, indent=2))
            return

        runtime_config = settings_service.resolve_admin_runtime(verbose=config.verbose)
    except SettingsError as err:
        raise SystemExit(str(err)) from err

    if isinstance(config.command, ApiCommand):
        uvicorn = _load_uvicorn("api", "api")
        api = build_api_app(runtime_config.library_path, settings_service)
        uvicorn.run(api.app, host="0.0.0.0", port=runtime_config.api_port)
        return

    if isinstance(config.command, UiCommand):
        uvicorn = _load_uvicorn("ui", "ui")
        ui = build_ui_app(runtime_config.library_path)
        uvicorn.run(ui.app, host="0.0.0.0", port=runtime_config.ui_port)
        return

    if isinstance(config.command, InteractiveCliCommand):
        interactive_cli = build_interactive_cli_controller(runtime_config.library_path)
        interactive_cli.run()
        return

    cli = build_cli_controller(runtime_config.library_path)
    cli.run(config.command)


if __name__ == "__main__":
    main()
