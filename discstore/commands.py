from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, model_validator


class CliTagSourceCommand(BaseModel):
    tag: str | None = None
    use_current_tag: bool = False

    @model_validator(mode="after")
    def validate_tag_source(self) -> Self:
        has_explicit_tag = bool(self.tag)
        if has_explicit_tag == self.use_current_tag:
            raise ValueError("Exactly one tag source must be provided: explicit tag or --from-current.")
        return self


class CliAddCommand(CliTagSourceCommand):
    type: Literal["add"]
    uri: str
    track: str | None = None
    artist: str | None = None
    album: str | None = None


class CliListCommandModes(StrEnum):
    table = "table"
    line = "line"


class CliListCommand(BaseModel):
    type: Literal["list"]
    mode: CliListCommandModes = CliListCommandModes.table


class CliRemoveCommand(CliTagSourceCommand):
    type: Literal["remove"]


class CliEditCommand(CliTagSourceCommand):
    type: Literal["edit"]
    uri: str | None = None
    track: str | None = None
    artist: str | None = None
    album: str | None = None


class CliGetCommand(CliTagSourceCommand):
    type: Literal["get"]


class CliSearchCommand(BaseModel):
    type: Literal["search"]
    query: str


class InteractiveCliCommand(BaseModel):
    type: Literal["interactive"]
