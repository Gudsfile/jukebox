from unittest.mock import MagicMock

from discstore.command_handlers import execute_library_command
from discstore.commands import CliSearchCommand, InteractiveCliCommand
from jukebox.settings.entities import ResolvedAdminRuntimeConfig


def test_execute_library_command_runs_standard_cli_with_resolved_library_path():
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=True,
    )
    command = CliSearchCommand(type="search", query="beatles")
    cli = MagicMock()
    build_cli_controller = MagicMock(return_value=cli)
    build_interactive_cli_controller = MagicMock()

    execute_library_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_cli_controller=build_cli_controller,
        build_interactive_cli_controller=build_interactive_cli_controller,
    )

    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    build_cli_controller.assert_called_once_with("/resolved/library.json")
    cli.run.assert_called_once_with(command)
    build_interactive_cli_controller.assert_not_called()


def test_execute_library_command_runs_interactive_cli_with_resolved_library_path():
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
    interactive_cli = MagicMock()
    build_cli_controller = MagicMock()
    build_interactive_cli_controller = MagicMock(return_value=interactive_cli)

    execute_library_command(
        verbose=False,
        command=InteractiveCliCommand(type="interactive"),
        settings_service=settings_service,
        build_cli_controller=build_cli_controller,
        build_interactive_cli_controller=build_interactive_cli_controller,
    )

    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=False)
    build_interactive_cli_controller.assert_called_once_with("/resolved/library.json")
    interactive_cli.run.assert_called_once_with()
    build_cli_controller.assert_not_called()
