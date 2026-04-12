from typing import Any, Dict, Optional

from pydantic import BaseModel, RootModel

from discstore.domain.entities import CurrentTagStatus, Disc


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class DiscPatchMetadataInput(BaseModel):
    artist: Optional[str] = None
    album: Optional[str] = None
    track: Optional[str] = None
    playlist: Optional[str] = None


class DiscPatchOptionInput(BaseModel):
    shuffle: Optional[bool] = None
    is_test: Optional[bool] = None


class DiscPatchInput(BaseModel):
    uri: Optional[str] = None
    metadata: Optional[DiscPatchMetadataInput] = None
    option: Optional[DiscPatchOptionInput] = None


class CurrentTagStatusOutput(CurrentTagStatus):
    pass


class SettingsResetInput(BaseModel):
    path: str


class SettingsPatchInput(RootModel[Dict[str, Any]]):
    pass
