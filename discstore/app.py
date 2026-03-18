from importlib import import_module

from discstore.adapters.inbound.config import ApiCommand, InteractiveCliCommand, UiCommand, parse_config
from discstore.di_container import build_api_app, build_cli_controller, build_interactive_cli_controller, build_ui_app
from jukebox.shared.dependency_messages import optional_extra_dependency_message
from jukebox.shared.logger import set_logger


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


def main():
    config = parse_config()
    set_logger("discstore", config.verbose)

    if isinstance(config.command, ApiCommand):
        uvicorn = _load_uvicorn("api", "api")
        api = build_api_app(config.library)
        uvicorn.run(api.app, host="0.0.0.0", port=config.command.port)
        return

    if isinstance(config.command, UiCommand):
        uvicorn = _load_uvicorn("ui", "ui")
        ui = build_ui_app(config.library)
        uvicorn.run(ui.app, host="0.0.0.0", port=config.command.port)
        return

    if isinstance(config.command, InteractiveCliCommand):
        interactive_cli = build_interactive_cli_controller(config.library)
        interactive_cli.run()
        return

    cli = build_cli_controller(config.library)
    cli.run(config.command)


if __name__ == "__main__":
    main()
