from discstore.adapters.inbound.config import ApiCommand, InteractiveCliCommand, UiCommand, parse_config
from discstore.di_container import build_api_app, build_cli_controller, build_interactive_cli_controller, build_ui_app
from jukebox.shared.logger import set_logger


def main():
    config = parse_config()
    set_logger("discstore", config.verbose)

    if isinstance(config.command, ApiCommand):
        import uvicorn  # type: ignore[unresolved-import]

        api = build_api_app(config.library)
        uvicorn.run(api.app, host="0.0.0.0", port=config.command.port)
        return

    if isinstance(config.command, UiCommand):
        import uvicorn  # type: ignore[unresolved-import]

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
