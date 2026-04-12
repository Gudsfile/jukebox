from typing import Any, Dict

from pydantic import BaseModel, RootModel

from discstore.domain.entities import CurrentTagStatus, Disc


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class CurrentTagStatusOutput(CurrentTagStatus):
    pass


class SettingsResetInput(BaseModel):
    path: str


class SettingsPatchInput(RootModel[Dict[str, Any]]):
    pass
