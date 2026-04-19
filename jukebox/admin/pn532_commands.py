from typing import Literal, Optional

from pydantic import BaseModel


class Pn532ProfilesCommand(BaseModel):
    type: Literal["pn532_profiles"]


class Pn532SelectCommand(BaseModel):
    type: Literal["pn532_select"]
    profile: Optional[str] = None


class Pn532ProbeCommand(BaseModel):
    type: Literal["pn532_probe"]


def is_pn532_command(command: object) -> bool:
    return isinstance(command, (Pn532ProfilesCommand, Pn532SelectCommand, Pn532ProbeCommand))
