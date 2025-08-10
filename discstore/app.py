from discstore.adapters.inbound.config import parse_config
from discstore.adapters.inbound.logger import set_logger
from discstore.di_container import build_api_app, build_cli_controller, build_interactive_cli_controller, build_ui_app


def main():
    config = parse_config()
    set_logger(config.verbose)

    if config.command.type == "api":
        import uvicorn

        api = build_api_app(config.library)
        uvicorn.run(api.app, host="0.0.0.0", port=config.command.port)
        return

    if config.command.type == "ui":
        import uvicorn

        ui = build_ui_app(config.library)
        uvicorn.run(ui.app, host="0.0.0.0", port=config.command.port)
        return

    if config.command.type == "interactive":
        interactive_cli = build_interactive_cli_controller(config.library)
        interactive_cli.run()
        return

    cli = build_cli_controller(config.library)
    cli.run(config.command)


if __name__ == "__main__":
    main()
