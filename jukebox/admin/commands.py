from typing import Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, model_validator


class ApiCommand(BaseModel):
    type: Literal["api"]
    port: Optional[int] = None


class UiCommand(BaseModel):
    type: Literal["ui"]
    port: Optional[int] = None


class SonosListCommand(BaseModel):
    type: Literal["sonos_list"]


class SonosSelectCommand(BaseModel):
    type: Literal["sonos_select"]
    uids: Optional[list[str]] = None
    coordinator: Optional[str] = None

    @model_validator(mode="after")
    def validate_coordinator_requires_uids(self):
        if self.coordinator is not None and not self.uids:
            raise ValueError("--coordinator requires --uids")
        return self


class SonosShowCommand(BaseModel):
    type: Literal["sonos_show"]


class SettingsShowCommand(BaseModel):
    type: Literal["settings_show"]
    effective: bool = False
    json_output: bool = False


class SettingsSetCommand(BaseModel):
    type: Literal["settings_set"]
    dotted_path: str
    value: str
    json_output: bool = False


class SettingsResetCommand(BaseModel):
    type: Literal["settings_reset"]
    dotted_path: str
    json_output: bool = False


AdminCommand = Union[
    ApiCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    SonosListCommand,
    SonosSelectCommand,
    SonosShowCommand,
    UiCommand,
]


def is_admin_command(command: object) -> bool:
    return isinstance(
        command,
        (
            ApiCommand,
            SettingsResetCommand,
            SettingsSetCommand,
            SettingsShowCommand,
            SonosListCommand,
            SonosSelectCommand,
            SonosShowCommand,
            UiCommand,
        ),
    )


def is_settings_command(command: object) -> bool:
    return isinstance(
        command,
        (
            SettingsResetCommand,
            SettingsSetCommand,
            SettingsShowCommand,
        ),
    )


def is_sonos_command(command: object) -> bool:
    return isinstance(command, (SonosListCommand, SonosSelectCommand, SonosShowCommand))
