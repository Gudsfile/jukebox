import argparse
import logging
import os
from enum import Enum
from typing import Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ValidationError

DEFAULT_LIBRARY_PATH = os.path.expanduser("~/.jukebox/library.json")
LOGGER = logging.getLogger("discstore")


try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version

try:
    __version__ = version("gukebox")
except PackageNotFoundError:
    __version__ = "unknown"


class CliAddCommand(BaseModel):
    type: Literal["add"]
    tag: str
    uri: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None


class CliListCommandModes(str, Enum):
    table = "table"
    line = "line"


class CliListCommand(BaseModel):
    type: Literal["list"]
    mode: CliListCommandModes = CliListCommandModes.table


class CliRemoveCommand(BaseModel):
    type: Literal["remove"]
    tag: str


class CliEditCommand(BaseModel):
    type: Literal["edit"]
    tag: str
    uri: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None


class InteractiveCliCommand(BaseModel):
    type: Literal["interactive"]


class ApiCommand(BaseModel):
    type: Literal["api"]
    port: int = 8000


class UiCommand(BaseModel):
    type: Literal["ui"]
    port: int = 8000


class CLIConfig(BaseModel):
    library: str
    verbose: bool = False

    command: Union[
        ApiCommand, InteractiveCliCommand, CliAddCommand, CliListCommand, CliRemoveCommand, CliEditCommand, UiCommand
    ]


def parse_config() -> CLIConfig:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--library",
        default=os.environ.get("JUKEBOX_LIBRARY_PATH", DEFAULT_LIBRARY_PATH),
        help="path to the library JSON file",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="show more details")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="show more details")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # CLI
    add_parser = subparsers.add_parser("add", help="Add a CD")
    add_parser.add_argument("tag", help="Tag to be associated with the CD")
    add_parser.add_argument("uri", help="Path or URI of the media file")
    add_parser.add_argument("--title", required=False, help="Name of the track")
    add_parser.add_argument("--artist", required=False, help="Name of the artist or band")
    add_parser.add_argument("--album", required=False, help="Name of the album")
    add_parser.add_argument("--opts", required=False, help="Playback options for the discs")

    list_parser = subparsers.add_parser("list", help="List all CDs")
    list_parser.add_argument("mode", choices=["line", "table"], help="Displaying mode")

    remove_parser = subparsers.add_parser("remove", help="Remove a CD")
    remove_parser.add_argument("tag", help="Tag to remove")

    edit_parser = subparsers.add_parser("edit", help="Edit a CD")
    edit_parser.add_argument("tag", help="Tag to be edited")
    edit_parser.add_argument("uri", help="Path or URI of the media file")
    edit_parser.add_argument("--title", required=False, help="Name of the track")
    edit_parser.add_argument("--artist", required=False, help="Name of the artist or band")
    edit_parser.add_argument("--album", required=False, help="Name of the album")
    edit_parser.add_argument("--opts", required=False, help="Playback options for the discs")

    # API
    api_parser = subparsers.add_parser("api", help="Start an API server")
    api_parser.add_argument("--port", type=int, default=8000, help="port")

    # UI
    _ = subparsers.add_parser("ui", help="Start an UI server")

    # Interactive
    _ = subparsers.add_parser("interactive", help="Run interactive CLI")

    args = parser.parse_args()
    args_dict = vars(args)

    base_data = {
        "library": args_dict.pop("library"),
        "verbose": args_dict.pop("verbose"),
    }

    command_name = args_dict.pop("command")
    command_data = {"type": command_name, **args_dict}

    config_data = {**base_data, "command": command_data}

    try:
        validated = CLIConfig(**config_data)
    except ValidationError as err:
        LOGGER.error("Config error", err)
        exit(1)

    return validated
