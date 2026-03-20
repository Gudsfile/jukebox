import argparse
import copy
import logging
import sys
from enum import Enum
from typing import Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ValidationError, model_validator

from jukebox.shared.config_utils import add_library_arg, add_verbose_arg, add_version_arg

LOGGER = logging.getLogger("discstore")


class CliTagSourceCommand(BaseModel):
    tag: Optional[str] = None
    use_current_tag: bool = False

    @model_validator(mode="after")
    def validate_tag_source(self):
        has_explicit_tag = bool(self.tag)
        if has_explicit_tag == self.use_current_tag:
            raise ValueError("Exactly one tag source must be provided: explicit tag or --from-current.")
        return self


class CliAddCommand(CliTagSourceCommand):
    type: Literal["add"]
    uri: str
    track: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None


class CliListCommandModes(str, Enum):
    table = "table"
    line = "line"


class CliListCommand(BaseModel):
    type: Literal["list"]
    mode: CliListCommandModes = CliListCommandModes.table


class CliRemoveCommand(CliTagSourceCommand):
    type: Literal["remove"]


class CliEditCommand(CliTagSourceCommand):
    type: Literal["edit"]
    uri: Optional[str] = None
    track: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None


class CliGetCommand(CliTagSourceCommand):
    type: Literal["get"]


class CliSearchCommand(BaseModel):
    type: Literal["search"]
    query: str


class InteractiveCliCommand(BaseModel):
    type: Literal["interactive"]


class ApiCommand(BaseModel):
    type: Literal["api"]
    port: int = 8000


class UiCommand(BaseModel):
    type: Literal["ui"]
    port: int = 8000


class DiscStoreConfig(BaseModel):
    library: str
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
        UiCommand,
    ]


def add_from_current_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--from-current",
        dest="use_current_tag",
        action="store_true",
        help="Resolve the tag ID from shared current-tag.txt state",
    )


def get_command_args(command_name: str) -> list[str]:
    argv = sys.argv[1:]
    command_index = argv.index(command_name)
    return argv[command_index + 1 :]


def is_ambiguous_add_from_current(command_args: list[str]) -> bool:
    flag_index = None
    positional_index = None
    option_args = {"--track", "--artist", "--album", "--opts"}
    skip_next = False

    for index, token in enumerate(command_args):
        if skip_next:
            skip_next = False
            continue

        if token in option_args:
            skip_next = True
            continue

        if token == "--from-current":
            flag_index = index
            continue

        if token == "--":
            if positional_index is None:
                positional_index = index + 1
            break

        if token.startswith("-"):
            continue

        if positional_index is None:
            positional_index = index

    return flag_index is not None and positional_index is not None and positional_index < flag_index


def parse_config() -> DiscStoreConfig:
    parser = argparse.ArgumentParser(
        prog="discstore",
        description="Manage your disc collection for jukebox",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Global arguments
    add_library_arg(parser)
    add_verbose_arg(parser)
    add_version_arg(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # CLI commands
    add_parser = subparsers.add_parser("add", help="Add a disc")
    add_from_current_arg(add_parser)
    add_parser.add_argument("tag", nargs="?", help="Tag to be associated with the disc")
    add_parser.add_argument("uri", nargs="?", help="Path or URI of the media file")
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
    api_parser.add_argument("--port", type=int, default=8000, help="port")

    # UI commands
    _ = subparsers.add_parser("ui", help="Start an UI server")

    # Interactive commands
    _ = subparsers.add_parser("interactive", help="Run interactive CLI")

    args = parser.parse_args()

    # Build command config
    args_dict = vars(copy.deepcopy(args))
    args_dict.pop("verbose")
    args_dict.pop("library")
    command_name = args_dict.pop("command")

    try:
        if (
            command_name == "add"
            and args_dict.get("use_current_tag")
            and is_ambiguous_add_from_current(get_command_args(command_name))
        ):
            raise ValueError("Ambiguous add invocation: place --from-current before the URI and do not pass a tag.")

        if (
            command_name == "add"
            and args_dict.get("use_current_tag")
            and args_dict.get("uri") is None
            and args_dict.get("tag")
        ):
            args_dict["uri"] = args_dict["tag"]
            args_dict["tag"] = None

        command_config = {"type": command_name, **args_dict}

        # Build and validate final config
        config = DiscStoreConfig(library=args.library, verbose=args.verbose, command=command_config)
    except (ValidationError, ValueError) as err:
        LOGGER.error("Config error: %s", err)
        exit(1)

    return config
