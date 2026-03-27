from enum import Enum
from typing import Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, model_validator


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


LibraryCommand = Union[
    CliAddCommand,
    CliListCommand,
    CliRemoveCommand,
    CliEditCommand,
    CliGetCommand,
    CliSearchCommand,
    InteractiveCliCommand,
]


def is_library_command(command: object) -> bool:
    return isinstance(
        command,
        (
            CliAddCommand,
            CliListCommand,
            CliRemoveCommand,
            CliEditCommand,
            CliGetCommand,
            CliSearchCommand,
            InteractiveCliCommand,
        ),
    )
