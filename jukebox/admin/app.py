import logging
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from discstore.command_handlers import execute_library_command
from discstore.commands import (
    CliAddCommand,
    CliEditCommand,
    CliGetCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    CliSearchCommand,
    InteractiveCliCommand,
)
from discstore.di_container import build_cli_controller, build_interactive_cli_controller
from jukebox.settings.errors import SettingsError
from jukebox.shared.config_utils import get_package_version
from jukebox.shared.logger import set_logger

from .command_handlers import execute_admin_command
from .commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from .di_container import build_admin_api_app, build_admin_ui_app, build_settings_service

LOGGER = logging.getLogger("jukebox-admin")


class AdminCliState:
    def __init__(self, library: Optional[str], verbose: bool):
        self.library = library
        self.verbose = verbose


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"jukebox-admin {get_package_version()}")
        raise typer.Exit()


def _get_state(ctx: typer.Context) -> AdminCliState:
    state = ctx.obj
    if not isinstance(state, AdminCliState):
        raise RuntimeError("Admin CLI state was not initialized")
    return state


def _run_command(ctx: typer.Context, command: object) -> None:
    state = _get_state(ctx)

    try:
        settings_service = build_settings_service(
            library=state.library,
            command=command,
            logger_warning=LOGGER.warning,
        )
        execute_admin_command(
            verbose=state.verbose,
            command=command,
            settings_service=settings_service,
            build_api_app=build_admin_api_app,
            build_ui_app=build_admin_ui_app,
            source_command="jukebox-admin",
        )
    except SettingsError as err:
        raise SystemExit(str(err)) from err


def _run_library_command(ctx: typer.Context, command: object) -> None:
    state = _get_state(ctx)

    try:
        settings_service = build_settings_service(
            library=state.library,
            command=command,
            logger_warning=LOGGER.warning,
        )
        execute_library_command(
            verbose=state.verbose,
            command=command,
            settings_service=settings_service,
            build_cli_controller=build_cli_controller,
            build_interactive_cli_controller=build_interactive_cli_controller,
        )
    except SettingsError as err:
        raise SystemExit(str(err)) from err


def _exit_on_command_validation_error(err: ValidationError) -> None:
    raise SystemExit(str(err)) from err


app = typer.Typer(help="Admin CLI for jukebox")
settings_app = typer.Typer(help="Inspect and manage application settings")
library_app = typer.Typer(help="Manage the library")
app.add_typer(settings_app, name="settings")
app.add_typer(library_app, name="library")


@app.callback()
def main_callback(
    ctx: typer.Context,
    library: Annotated[
        Optional[str],
        typer.Option("--library", "-l", help="override the library JSON path for this process"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="enable verbose logging"),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="show current installed version",
        ),
    ] = False,
) -> None:
    del version
    set_logger("jukebox-admin", verbose)
    ctx.obj = AdminCliState(library=library, verbose=verbose)


@settings_app.command("show")
def settings_show(
    ctx: typer.Context,
    effective: Annotated[
        bool,
        typer.Option("--effective", help="show merged effective settings with provenance"),
    ] = False,
) -> None:
    _run_command(ctx, SettingsShowCommand(type="settings_show", effective=effective))


@settings_app.command("set")
def settings_set(
    ctx: typer.Context,
    dotted_path: Annotated[str, typer.Argument(help="canonical dotted path to update")],
    value: Annotated[str, typer.Argument(help="value to persist for the given path")],
) -> None:
    _run_command(ctx, SettingsSetCommand(type="settings_set", dotted_path=dotted_path, value=value))


@settings_app.command("reset")
def settings_reset(
    ctx: typer.Context,
    dotted_path: Annotated[str, typer.Argument(help="canonical dotted path to reset")],
) -> None:
    _run_command(ctx, SettingsResetCommand(type="settings_reset", dotted_path=dotted_path))


@app.command("api")
def api(
    ctx: typer.Context,
    port: Annotated[
        Optional[int],
        typer.Option("--port", help="override the configured API port"),
    ] = None,
) -> None:
    _run_command(ctx, ApiCommand(type="api", port=port))


@app.command("ui")
def ui(
    ctx: typer.Context,
    port: Annotated[
        Optional[int],
        typer.Option("--port", help="override the configured UI port"),
    ] = None,
) -> None:
    _run_command(ctx, UiCommand(type="ui", port=port))


@library_app.command("add")
def library_add(
    ctx: typer.Context,
    tag: Annotated[Optional[str], typer.Argument(help="Tag to be associated with the disc")] = None,
    uri: Annotated[str, typer.Option("--uri", help="Path or URI of the media file")] = ...,
    track: Annotated[Optional[str], typer.Option("--track", help="Name of the track")] = None,
    artist: Annotated[Optional[str], typer.Option("--artist", help="Name of the artist or band")] = None,
    album: Annotated[Optional[str], typer.Option("--album", help="Name of the album")] = None,
    use_current_tag: Annotated[
        bool,
        typer.Option("--from-current", help="Resolve the tag ID from shared current-tag.txt state"),
    ] = False,
) -> None:
    try:
        command = CliAddCommand(
            type="add",
            tag=tag,
            use_current_tag=use_current_tag,
            uri=uri,
            track=track,
            artist=artist,
            album=album,
        )
    except ValidationError as err:
        _exit_on_command_validation_error(err)

    _run_library_command(ctx, command)


@library_app.command("list")
def library_list(
    ctx: typer.Context,
    mode: Annotated[CliListCommandModes, typer.Argument(help="Displaying mode")],
) -> None:
    _run_library_command(ctx, CliListCommand(type="list", mode=mode))


@library_app.command("remove")
def library_remove(
    ctx: typer.Context,
    tag: Annotated[Optional[str], typer.Argument(help="Tag to remove")] = None,
    use_current_tag: Annotated[
        bool,
        typer.Option("--from-current", help="Resolve the tag ID from shared current-tag.txt state"),
    ] = False,
) -> None:
    try:
        command = CliRemoveCommand(type="remove", tag=tag, use_current_tag=use_current_tag)
    except ValidationError as err:
        _exit_on_command_validation_error(err)

    _run_library_command(ctx, command)


@library_app.command("edit")
def library_edit(
    ctx: typer.Context,
    tag: Annotated[Optional[str], typer.Argument(help="Tag to be edited")] = None,
    uri: Annotated[Optional[str], typer.Option("--uri", help="Path or URI of the media file")] = None,
    track: Annotated[Optional[str], typer.Option("--track", help="Name of the track")] = None,
    artist: Annotated[Optional[str], typer.Option("--artist", help="Name of the artist or band")] = None,
    album: Annotated[Optional[str], typer.Option("--album", help="Name of the album")] = None,
    use_current_tag: Annotated[
        bool,
        typer.Option("--from-current", help="Resolve the tag ID from shared current-tag.txt state"),
    ] = False,
) -> None:
    try:
        command = CliEditCommand(
            type="edit",
            tag=tag,
            use_current_tag=use_current_tag,
            uri=uri,
            track=track,
            artist=artist,
            album=album,
        )
    except ValidationError as err:
        _exit_on_command_validation_error(err)

    _run_library_command(ctx, command)


@library_app.command("get")
def library_get(
    ctx: typer.Context,
    tag: Annotated[Optional[str], typer.Argument(help="Tag to retrieve")] = None,
    use_current_tag: Annotated[
        bool,
        typer.Option("--from-current", help="Resolve the tag ID from shared current-tag.txt state"),
    ] = False,
) -> None:
    try:
        command = CliGetCommand(type="get", tag=tag, use_current_tag=use_current_tag)
    except ValidationError as err:
        _exit_on_command_validation_error(err)

    _run_library_command(ctx, command)


@library_app.command("search")
def library_search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query (matches artist, album, track, playlist, or tag)")],
) -> None:
    _run_library_command(ctx, CliSearchCommand(type="search", query=query))


@library_app.command("interactive")
def library_interactive(ctx: typer.Context) -> None:
    _run_library_command(ctx, InteractiveCliCommand(type="interactive"))


def main(args: Optional[list[str]] = None) -> None:
    app(args=args, prog_name="jukebox-admin")
