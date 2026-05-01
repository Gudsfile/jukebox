from typing import Any

from pydantic import BaseModel, RootModel

from discstore.domain.entities import CurrentTagStatus, Disc


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class DiscPatchMetadataInput(BaseModel):
    artist: str | None = None
    album: str | None = None
    track: str | None = None
    playlist: str | None = None


class DiscPatchOptionInput(BaseModel):
    shuffle: bool | None = None
    is_test: bool | None = None


class DiscPatchInput(BaseModel):
    uri: str | None = None
    metadata: DiscPatchMetadataInput | None = None
    option: DiscPatchOptionInput | None = None


class CurrentTagStatusOutput(CurrentTagStatus):
    pass


class CurrentTagDiscOutput(BaseModel):
    tag_id: str
    disc: DiscOutput


class SettingsResetInput(BaseModel):
    path: str


class SettingsPatchInput(RootModel[dict[str, Any]]):
    pass
