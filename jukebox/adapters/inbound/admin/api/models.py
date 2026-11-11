from typing import Any

from pydantic import BaseModel, RootModel, computed_field

from jukebox.domain.entities import CurrentTagStatus, Disc
from jukebox.settings.entities import SelectedSonosGroupSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    @computed_field
    @property
    def display_type(self) -> str:
        return self.metadata.display_type

    @computed_field
    @property
    def display_title(self) -> str:
        return self.metadata.display_title


class DiscPatchMetadataInput(BaseModel):
    artist: str | None = None
    album: str | None = None
    track: str | None = None
    playlist: str | None = None


class DiscPatchOptionInput(BaseModel):
    shuffle: bool | None = None


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


class SettingChoiceOutput(BaseModel):
    value: str
    label: str


class EditableSettingDisplayOutput(BaseModel):
    path: str
    label: str
    description: str
    field_type: str
    section: str
    section_label: str
    section_description: str
    section_sort_order: int
    requires_restart: bool
    advanced: bool
    choices: list[SettingChoiceOutput]
    default_value: Any
    persisted_value: Any
    effective_value: Any
    provenance: str
    is_persisted: bool
    is_pinned_default: bool


class SettingsDisplaysOutput(BaseModel):
    settings: list[EditableSettingDisplayOutput]
    effective_settings_error: str | None = None


class SonosSpeakerOutput(DiscoveredSonosSpeaker):
    pass


class SelectedSonosGroupOutput(SelectedSonosGroupSettings):
    pass


class SonosSelectionMemberAvailabilityOutput(BaseModel):
    uid: str
    status: str
    speaker: SonosSpeakerOutput | None = None


class SonosSelectionAvailabilityOutput(BaseModel):
    status: str
    members: list[SonosSelectionMemberAvailabilityOutput]


class SonosSelectionOutput(BaseModel):
    selected_group: SelectedSonosGroupOutput | None = None
    availability: SonosSelectionAvailabilityOutput


class SonosSelectionInput(BaseModel):
    uids: list[str]
    coordinator_uid: str | None = None


class SonosSelectionUpdateOutput(BaseModel):
    selected_group: SelectedSonosGroupOutput
    availability: SonosSelectionAvailabilityOutput
    message: str
    restart_required: bool
