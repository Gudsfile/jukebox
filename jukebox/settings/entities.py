import os
from typing import Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from jukebox.shared.timing import MIN_PAUSE_DELAY_SECONDS

from .runtime_validation import validate_resolved_jukebox_runtime_rules


def _resolve_default_library_path():
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    return os.path.expanduser(os.path.join(xdg_config_home, "jukebox/library.json"))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectedSonosSpeakerSettings(StrictModel):
    uid: str


class SelectedSonosGroupSettings(StrictModel):
    coordinator_uid: str
    members: list[SelectedSonosSpeakerSettings]

    @model_validator(mode="after")
    def validate_group_shape(self):
        if not self.members:
            raise ValueError("selected_group must include at least one member")

        member_uids = [member.uid for member in self.members]
        if len(set(member_uids)) != len(member_uids):
            raise ValueError("selected_group.members must not contain duplicate uids")

        if self.coordinator_uid not in member_uids:
            raise ValueError("selected_group.coordinator_uid must match a member uid")

        return self


class PersistedSonosPlayerSettings(StrictModel):
    selected_group: Optional[SelectedSonosGroupSettings] = None


class SonosPlayerSettings(PersistedSonosPlayerSettings):
    manual_host: Optional[str] = None
    manual_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_manual_target(self):
        if self.manual_host and self.manual_name:
            raise ValueError("manual_host and manual_name are mutually exclusive")
        return self


class PersistedPlayerSettings(StrictModel):
    type: Literal["dryrun", "sonos"] = "dryrun"
    sonos: PersistedSonosPlayerSettings = Field(default_factory=PersistedSonosPlayerSettings)


class PlayerSettings(PersistedPlayerSettings):
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


class PersistedJukeboxSettings(StrictModel):
    player: PersistedPlayerSettings = Field(default_factory=PersistedPlayerSettings)
    reader: ReaderSettings = Field(default_factory=ReaderSettings)
    playback: PlaybackSettings = Field(default_factory=PlaybackSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


class JukeboxSettings(PersistedJukeboxSettings):
    player: PlayerSettings = Field(default_factory=PlayerSettings)


class ServerSettings(StrictModel):
    port: int = Field(default=8000, ge=1, le=65535)


class PathsSettings(StrictModel):
    library_path: str = _resolve_default_library_path()


class AdminSettings(StrictModel):
    api: ServerSettings = Field(default_factory=ServerSettings)
    ui: ServerSettings = Field(default_factory=ServerSettings)


class PersistedAppSettings(StrictModel):
    schema_version: int = 1
    paths: PathsSettings = Field(default_factory=PathsSettings)
    jukebox: PersistedJukeboxSettings = Field(default_factory=PersistedJukeboxSettings)
    admin: AdminSettings = Field(default_factory=AdminSettings)


class AppSettings(PersistedAppSettings):
    jukebox: JukeboxSettings = Field(default_factory=JukeboxSettings)


class SparseSelectedSonosSpeakerSettings(StrictModel):
    uid: Optional[str] = None


class SparseSelectedSonosGroupSettings(StrictModel):
    coordinator_uid: Optional[str] = None
    members: Optional[list[SparseSelectedSonosSpeakerSettings]] = None


class SparsePersistedSonosPlayerSettings(StrictModel):
    selected_group: Optional[SparseSelectedSonosGroupSettings] = None


class SparseSonosPlayerSettings(SparsePersistedSonosPlayerSettings):
    manual_host: Optional[str] = None
    manual_name: Optional[str] = None


class SparsePersistedPlayerSettings(StrictModel):
    type: Optional[Literal["dryrun", "sonos"]] = None
    sonos: Optional[SparsePersistedSonosPlayerSettings] = None


class SparsePlayerSettings(SparsePersistedPlayerSettings):
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


class SparsePersistedJukeboxSettings(StrictModel):
    player: Optional[SparsePersistedPlayerSettings] = None
    reader: Optional[SparseReaderSettings] = None
    playback: Optional[SparsePlaybackSettings] = None
    runtime: Optional[SparseRuntimeSettings] = None


class SparseJukeboxSettings(SparsePersistedJukeboxSettings):
    player: Optional[SparsePlayerSettings] = None


class SparseServerSettings(StrictModel):
    port: Optional[int] = None


class SparsePathsSettings(StrictModel):
    library_path: Optional[str] = None


class SparseAdminSettings(StrictModel):
    api: Optional[SparseServerSettings] = None
    ui: Optional[SparseServerSettings] = None


class SparsePersistedAppSettings(StrictModel):
    schema_version: int
    paths: Optional[SparsePathsSettings] = None
    jukebox: Optional[SparsePersistedJukeboxSettings] = None
    admin: Optional[SparseAdminSettings] = None


class SparseAppSettings(SparsePersistedAppSettings):
    jukebox: Optional[SparseJukeboxSettings] = None


class ResolvedSonosSpeakerRuntime(StrictModel):
    uid: str
    name: str
    host: str
    household_id: str


class ResolvedSonosGroupRuntime(StrictModel):
    household_id: str
    coordinator: ResolvedSonosSpeakerRuntime
    members: list[ResolvedSonosSpeakerRuntime]
    missing_member_uids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_group_shape(self):
        if not self.members:
            raise ValueError("resolved Sonos group must include at least one member")

        member_uids = {member.uid for member in self.members}
        if self.coordinator.uid not in member_uids:
            raise ValueError("resolved Sonos group coordinator must be present in members")

        household_ids = {member.household_id for member in self.members}
        if household_ids != {self.household_id}:
            raise ValueError("resolved Sonos group members must belong to the same household")

        reachable_member_uids = {member.uid for member in self.members}
        missing_member_uids = set(self.missing_member_uids)
        if reachable_member_uids & missing_member_uids:
            raise ValueError("resolved Sonos group missing_member_uids must not overlap with resolved members")

        return self

    @property
    def desired_member_uids(self) -> set[str]:
        return {member.uid for member in self.members} | set(self.missing_member_uids)

    @property
    def is_partial(self) -> bool:
        return bool(self.missing_member_uids)


class ResolvedJukeboxRuntimeConfig(StrictModel):
    library_path: str
    player_type: Literal["dryrun", "sonos"]
    sonos_host: Optional[str] = None
    sonos_name: Optional[str] = None
    sonos_group: Optional[ResolvedSonosGroupRuntime] = None
    reader_type: Literal["dryrun", "nfc"]
    pause_duration_seconds: int
    pause_delay_seconds: float
    loop_interval_seconds: float
    nfc_read_timeout_seconds: float
    verbose: bool = False

    @model_validator(mode="after")
    def validate_runtime_rules(self):
        validate_resolved_jukebox_runtime_rules(self)
        return self


class ResolvedAdminRuntimeConfig(StrictModel):
    library_path: str
    api_port: int
    ui_port: int
    verbose: bool = False
