from typing import Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from jukebox.shared.timing import MIN_PAUSE_DELAY_SECONDS

from .validation_rules import validate_settings_rules
from .value_providers import ObjectLeafValueProvider


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectedSonosSpeakerSettings(StrictModel):
    uid: str
    name: str
    household_id: Optional[str] = None
    last_known_host: Optional[str] = None


class SelectedSonosGroupSettings(StrictModel):
    household_id: Optional[str] = None
    coordinator_uid: str
    members: list[SelectedSonosSpeakerSettings]


class SonosPlayerSettings(StrictModel):
    manual_host: Optional[str] = None
    manual_name: Optional[str] = None
    selected_group: Optional[SelectedSonosGroupSettings] = None

    @model_validator(mode="after")
    def validate_manual_target(self):
        if self.manual_host and self.manual_name:
            raise ValueError("manual_host and manual_name are mutually exclusive")
        return self


class PlayerSettings(StrictModel):
    type: Literal["dryrun", "sonos"] = "dryrun"
    sonos: SonosPlayerSettings = Field(default_factory=SonosPlayerSettings)


class NfcReaderSettings(StrictModel):
    read_timeout_seconds: float = Field(default=0.1, gt=0)


class ReaderSettings(StrictModel):
    type: Literal["dryrun", "nfc"] = "dryrun"
    nfc: NfcReaderSettings = Field(default_factory=NfcReaderSettings)


class PlaybackSettings(StrictModel):
    pause_duration_seconds: int = Field(default=900, gt=0)
    pause_delay_seconds: float = Field(default=0.25, ge=MIN_PAUSE_DELAY_SECONDS)


class RuntimeSettings(StrictModel):
    loop_interval_seconds: float = Field(default=0.1, gt=0)


class JukeboxSettings(StrictModel):
    player: PlayerSettings = Field(default_factory=PlayerSettings)
    reader: ReaderSettings = Field(default_factory=ReaderSettings)
    playback: PlaybackSettings = Field(default_factory=PlaybackSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


class ServerSettings(StrictModel):
    port: int = Field(default=8000, ge=1, le=65535)


class PathsSettings(StrictModel):
    library_path: str = "~/.jukebox/library.json"


class AdminSettings(StrictModel):
    api: ServerSettings = Field(default_factory=ServerSettings)
    ui: ServerSettings = Field(default_factory=ServerSettings)


class AppSettings(StrictModel):
    schema_version: int = 1
    paths: PathsSettings = Field(default_factory=PathsSettings)
    jukebox: JukeboxSettings = Field(default_factory=JukeboxSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)


class SparseSelectedSonosSpeakerSettings(StrictModel):
    uid: Optional[str] = None
    name: Optional[str] = None
    household_id: Optional[str] = None
    last_known_host: Optional[str] = None


class SparseSelectedSonosGroupSettings(StrictModel):
    household_id: Optional[str] = None
    coordinator_uid: Optional[str] = None
    members: Optional[list[SparseSelectedSonosSpeakerSettings]] = None


class SparseSonosPlayerSettings(StrictModel):
    manual_host: Optional[str] = None
    manual_name: Optional[str] = None
    selected_group: Optional[SparseSelectedSonosGroupSettings] = None


class SparsePlayerSettings(StrictModel):
    type: Optional[Literal["dryrun", "sonos"]] = None
    sonos: Optional[SparseSonosPlayerSettings] = None


class SparseNfcReaderSettings(StrictModel):
    read_timeout_seconds: Optional[float] = None


class SparseReaderSettings(StrictModel):
    type: Optional[Literal["dryrun", "nfc"]] = None
    nfc: Optional[SparseNfcReaderSettings] = None


class SparsePlaybackSettings(StrictModel):
    pause_duration_seconds: Optional[int] = None
    pause_delay_seconds: Optional[float] = None


class SparseRuntimeSettings(StrictModel):
    loop_interval_seconds: Optional[float] = None


class SparseJukeboxSettings(StrictModel):
    player: Optional[SparsePlayerSettings] = None
    reader: Optional[SparseReaderSettings] = None
    playback: Optional[SparsePlaybackSettings] = None
    runtime: Optional[SparseRuntimeSettings] = None


class SparseServerSettings(StrictModel):
    port: Optional[int] = None


class SparsePathsSettings(StrictModel):
    library_path: Optional[str] = None


class SparseAdminSettings(StrictModel):
    api: Optional[SparseServerSettings] = None
    ui: Optional[SparseServerSettings] = None


class SparseAppSettings(StrictModel):
    schema_version: int
    paths: Optional[SparsePathsSettings] = None
    jukebox: Optional[SparseJukeboxSettings] = None
    admin: Optional[SparseAdminSettings] = None


class ResolvedJukeboxRuntimeConfig(StrictModel):
    library_path: str
    player_type: Literal["dryrun", "sonos"]
    sonos_host: Optional[str] = None
    sonos_name: Optional[str] = None
    reader_type: Literal["dryrun", "nfc"]
    pause_duration_seconds: int
    pause_delay_seconds: float
    loop_interval_seconds: float
    nfc_read_timeout_seconds: float
    verbose: bool = False

    @model_validator(mode="after")
    def validate_timing_relationships(self):
        validate_settings_rules(ObjectLeafValueProvider(self))
        return self


class ResolvedAdminRuntimeConfig(StrictModel):
    library_path: str
    api_port: int
    ui_port: int
    verbose: bool = False
