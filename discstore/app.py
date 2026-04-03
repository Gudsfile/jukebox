import logging
import sys
import traceback

from discstore.adapters.inbound.config import (
    DiscStoreConfig,
    parse_config,
)
from discstore.command_handlers import execute_library_command
from discstore.commands import is_library_command
from discstore.di_container import build_cli_controller, build_interactive_cli_controller
from jukebox.admin.cli_presentation import render_cli_error
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
            try:
                execute_admin_command(
                    verbose=config.verbose,
                    command=config.command,
                    settings_service=settings_service,
                    build_api_app=build_admin_api_app,
                    build_ui_app=build_admin_ui_app,
                    source_command="discstore",
                    library=config.library,
                )
            except RuntimeError as err:
                print(str(err), file=sys.stderr)
                raise SystemExit(1) from err
            return

        if is_library_command(config.command):
            try:
                execute_library_command(
                    verbose=config.verbose,
                    command=config.command,
                    settings_service=settings_service,
                    build_cli_controller=build_cli_controller,
                    build_interactive_cli_controller=build_interactive_cli_controller,
                )
            except (ValueError, RuntimeError) as err:
                print(str(err), file=sys.stderr)
                raise SystemExit(1) from err
            return

    except SystemExit as err:
        if isinstance(err.code, str):
            print(render_cli_error(err, verbose=config.verbose), file=sys.stderr)
            raise SystemExit(1) from err
        raise
    except SettingsError as err:
        print(render_cli_error(err, verbose=config.verbose), file=sys.stderr)
        raise SystemExit(1) from err
    except OSError as err:
        print(str(err), file=sys.stderr)
        raise SystemExit(1) from err
    except Exception as err:
        print(render_cli_error(err, verbose=config.verbose), file=sys.stderr)
        if config.verbose:
            traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)
        raise SystemExit(1) from err

    raise TypeError("Unsupported discstore command")


if __name__ == "__main__":
    main()
