import argparse
import logging
from typing import Optional, Union

from pydantic import BaseModel, ValidationError

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
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from jukebox.shared.config_utils import add_verbose_arg, add_version_arg

LOGGER = logging.getLogger("discstore")

__all__ = [
    "ApiCommand",
    "CliAddCommand",
    "CliEditCommand",
    "CliGetCommand",
    "CliListCommand",
    "CliListCommandModes",
    "CliRemoveCommand",
    "CliSearchCommand",
    "DiscStoreConfig",
    "InteractiveCliCommand",
    "SettingsResetCommand",
    "SettingsSetCommand",
    "SettingsShowCommand",
    "UiCommand",
    "add_from_current_arg",
    "parse_config",
]


class DiscStoreConfig(BaseModel):
    library: Optional[str] = None
    verbose: bool = False

    command: Union[
        ApiCommand,
        InteractiveCliCommand,
        CliAddCommand,
        CliListCommand,
        CliRemoveCommand,
        CliEditCommand,
        CliGetCommand,
        CliSearchCommand,
        SettingsResetCommand,
        SettingsSetCommand,
        SettingsShowCommand,
        UiCommand,
    ]


def add_from_current_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--from-current",
        dest="use_current_tag",
        action="store_true",
        help="Resolve the tag ID from shared current-tag.txt state",
    )


def _build_library_command(command_name: str, args: argparse.Namespace):
    if command_name == "add":
        return CliAddCommand(
            type="add",
            tag=args.tag,
            use_current_tag=args.use_current_tag,
            uri=args.uri,
            track=args.track,
            artist=args.artist,
            album=args.album,
        )
    if command_name == "list":
        return CliListCommand(type="list", mode=args.mode)
    if command_name == "remove":
        return CliRemoveCommand(type="remove", tag=args.tag, use_current_tag=args.use_current_tag)
    if command_name == "edit":
        return CliEditCommand(
            type="edit",
            tag=args.tag,
            use_current_tag=args.use_current_tag,
            uri=args.uri,
            track=args.track,
            artist=args.artist,
            album=args.album,
        )
    if command_name == "get":
        return CliGetCommand(type="get", tag=args.tag, use_current_tag=args.use_current_tag)
    if command_name == "search":
        return CliSearchCommand(type="search", query=args.query)
    if command_name == "interactive":
        return InteractiveCliCommand(type="interactive")
    raise ValueError(f"Unsupported command: {command_name}")


def _build_admin_command(args: argparse.Namespace):
    if args.command == "api":
        return ApiCommand(type="api", port=args.port)
    if args.command == "ui":
        return UiCommand(type="ui", port=args.port)
    if args.command != "settings":
        raise ValueError(f"Unsupported admin command: {args.command}")

    if args.settings_command == "show":
        return SettingsShowCommand(type="settings_show", effective=args.effective)
    if args.settings_command == "set":
        return SettingsSetCommand(type="settings_set", dotted_path=args.dotted_path, value=args.value)
    if args.settings_command == "reset":
        return SettingsResetCommand(type="settings_reset", dotted_path=args.dotted_path)
    raise ValueError(f"Unsupported settings command: {args.settings_command}")


def parse_config() -> DiscStoreConfig:
    parser = argparse.ArgumentParser(
        prog="discstore",
        description="Manage your disc collection for jukebox",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-l",
        "--library",
        default=None,
        help="override the library JSON path for this process",
    )
    add_verbose_arg(parser)
    add_version_arg(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # CLI commands
    add_parser = subparsers.add_parser("add", help="Add a disc")
    add_from_current_arg(add_parser)
    add_parser.add_argument("tag", nargs="?", help="Tag to be associated with the disc")
    add_parser.add_argument("--uri", required=True, help="Path or URI of the media file")
    add_parser.add_argument("--track", required=False, help="Name of the track")
    add_parser.add_argument("--artist", required=False, help="Name of the artist or band")
    add_parser.add_argument("--album", required=False, help="Name of the album")
    add_parser.add_argument("--opts", required=False, help="Playback options for the discs")

    list_parser = subparsers.add_parser("list", help="List all discs")
    list_parser.add_argument("mode", choices=["line", "table"], help="Displaying mode")

    remove_parser = subparsers.add_parser("remove", help="Remove a disc")
    add_from_current_arg(remove_parser)
    remove_parser.add_argument("tag", nargs="?", help="Tag to remove")

    edit_parser = subparsers.add_parser("edit", help="Edit a disc (partial updates supported)")
    add_from_current_arg(edit_parser)
    edit_parser.add_argument("tag", nargs="?", help="Tag to be edited")
    edit_parser.add_argument("--uri", required=False, help="Path or URI of the media file")
    edit_parser.add_argument("--track", required=False, help="Name of the track")
    edit_parser.add_argument("--artist", required=False, help="Name of the artist or band")
    edit_parser.add_argument("--album", required=False, help="Name of the album")
    edit_parser.add_argument("--opts", required=False, help="Playback options for the discs")

    get_parser = subparsers.add_parser("get", help="Get a disc by tag ID")
    add_from_current_arg(get_parser)
    get_parser.add_argument("tag", nargs="?", help="Tag to retrieve")

    search_parser = subparsers.add_parser("search", help="Search discs by query")
    search_parser.add_argument("query", help="Search query (matches artist, album, track, playlist, or tag)")

    # API commands
    api_parser = subparsers.add_parser("api", help="Start an API server")
    api_parser.add_argument("--port", type=int, default=None, help="override the configured API port")

    # UI commands
    ui_parser = subparsers.add_parser("ui", help="Start an UI server")
    ui_parser.add_argument("--port", type=int, default=None, help="override the configured UI port")

    # Interactive commands
    _ = subparsers.add_parser("interactive", help="Run interactive CLI")

    settings_parser = subparsers.add_parser("settings", help="Inspect application settings")
    settings_subparsers = settings_parser.add_subparsers(dest="settings_command", required=True)
    settings_show_parser = settings_subparsers.add_parser("show", help="Show persisted settings")
    settings_show_parser.add_argument(
        "--effective",
        action="store_true",
        help="show merged effective settings with provenance",
    )
    settings_set_parser = settings_subparsers.add_parser("set", help="Set a persisted setting override")
    settings_set_parser.add_argument("dotted_path", help="canonical dotted path to update")
    settings_set_parser.add_argument("value", help="value to persist for the given path")
    settings_reset_parser = settings_subparsers.add_parser("reset", help="Remove a persisted setting override")
    settings_reset_parser.add_argument("dotted_path", help="canonical dotted path to reset")

    args = parser.parse_args()

    # Build command config
    try:
        command = (
            _build_admin_command(args)
            if args.command in {"api", "ui", "settings"}
            else _build_library_command(args.command, args)
        )
        config = DiscStoreConfig(library=args.library, verbose=args.verbose, command=command)
    except (ValidationError, ValueError) as err:
        LOGGER.error("Config error: %s", err)
        exit(1)

    return config
