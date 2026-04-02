import logging

from discstore.adapters.inbound.config import (
    DiscStoreConfig,
    InteractiveCliCommand,
    parse_config,
)
from discstore.di_container import build_cli_controller, build_interactive_cli_controller
from jukebox.admin.command_handlers import execute_admin_command
from jukebox.admin.commands import is_admin_command
from jukebox.admin.di_container import (
    build_admin_api_app,
    build_admin_ui_app,
)
from jukebox.admin.di_container import (
    build_settings_service as build_admin_settings_service,
)
from jukebox.settings.errors import SettingsError
from jukebox.shared.logger import set_logger

LOGGER = logging.getLogger("discstore")


def _build_settings_service(config: DiscStoreConfig):
    return build_admin_settings_service(
        library=config.library,
        command=config.command,
        logger_warning=LOGGER.warning,
    )


def main():
    config = parse_config()
    set_logger("discstore", config.verbose)
    try:
        settings_service = _build_settings_service(config)
        if is_admin_command(config.command):
            execute_admin_command(
                verbose=config.verbose,
                command=config.command,
                settings_service=settings_service,
                build_api_app=build_admin_api_app,
                build_ui_app=build_admin_ui_app,
                source_command="discstore",
            )
            return

        runtime_config = settings_service.resolve_admin_runtime(verbose=config.verbose)
    except SettingsError as err:
        raise SystemExit(str(err)) from err

    if isinstance(config.command, InteractiveCliCommand):
        interactive_cli = build_interactive_cli_controller(runtime_config.library_path)
        interactive_cli.run()
        return

    cli = build_cli_controller(runtime_config.library_path)
    cli.run(config.command)


if __name__ == "__main__":
    main()
