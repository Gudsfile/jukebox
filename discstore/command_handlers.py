from typing import Callable, Protocol

from jukebox.settings.service_protocols import SettingsService

from .commands import InteractiveCliCommand


class LibraryController(Protocol):
    def run(self, command: object) -> None: ...


class InteractiveLibraryController(Protocol):
    def run(self) -> None: ...


def execute_library_command(
    verbose: bool,
    command: object,
    settings_service: SettingsService,
    build_cli_controller: Callable[[str], LibraryController],
    build_interactive_cli_controller: Callable[[str], InteractiveLibraryController],
) -> None:
    runtime_config = settings_service.resolve_admin_runtime(verbose=verbose)

    if isinstance(command, InteractiveCliCommand):
        interactive_cli = build_interactive_cli_controller(runtime_config.library_path)
        interactive_cli.run()
        return

    cli = build_cli_controller(runtime_config.library_path)
    cli.run(command)
