from typing import Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel


class ApiCommand(BaseModel):
    type: Literal["api"]
    port: Optional[int] = None


class UiCommand(BaseModel):
    type: Literal["ui"]
    port: Optional[int] = None


class SettingsShowCommand(BaseModel):
    type: Literal["settings_show"]
    effective: bool = False


class SettingsSetCommand(BaseModel):
    type: Literal["settings_set"]
    dotted_path: str
    value: str


class SettingsResetCommand(BaseModel):
    type: Literal["settings_reset"]
    dotted_path: str


AdminCommand = Union[
    ApiCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
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
            UiCommand,
        ),
    )
