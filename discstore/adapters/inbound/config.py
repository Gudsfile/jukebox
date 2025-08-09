import argparse
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, ValidationError


class Command(BaseModel):
    type: str


class CliAddCommand(Command):
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


class InteractiveCliCommand(Command):
    type: Literal["interactive"]


class ApiCommand(Command):
    type: Literal["api"]
    port: int = 8000


class CLIConfig(BaseModel):
    library: str = Field(..., alias="library_path")
    verbose: bool = False

    command: Union[ApiCommand, InteractiveCliCommand, CliAddCommand, CliListCommand]


def parse_config() -> CLIConfig:
    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--library-path", required=True, help="Library file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Mode verbeux")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # CLI
    add_parser = subparsers.add_parser("add", help="Ajouter un CD")
    add_parser.add_argument("tag", help="Tag du CD")
    add_parser.add_argument("uri", help="URI du CD")
    add_parser.add_argument("--title", required=False, help="Titre")
    add_parser.add_argument("--artist", required=False, help="Artiste")
    add_parser.add_argument("--album", required=False, help="Album")
    add_parser.add_argument("--opts", required=False, help="Options")

    list_parser = subparsers.add_parser("list", help="Lister les CDs")
    list_parser.add_argument("mode", choices=["line", "table"], help="Mode d'affichage")

    # API
    api_parser = subparsers.add_parser("api", help="Lancer le serveur API")
    api_parser.add_argument("--port", type=int, default=8000, help="Port API")

    # Interactive
    _ = subparsers.add_parser("interactive", help="Run interactive CLI")

    args = parser.parse_args()
    args_dict = vars(args)

    base_data = {
        "library_path": args_dict.pop("library_path"),
        "verbose": args_dict.pop("verbose"),
    }

    command_name = args_dict.pop("command")
    command_data = {"type": command_name, **args_dict}

    config_data = {**base_data, "command": command_data}

    try:
        validated = CLIConfig(**config_data)
    except ValidationError as e:
        print("\n[CONFIG ERROR]")
        print(e)
        exit(1)

    return validated
