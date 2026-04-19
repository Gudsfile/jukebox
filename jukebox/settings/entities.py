import os
from typing import Literal

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
    household_id: str | None = Field(default=None, exclude_if=lambda value: value is None)
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
    selected_group: SelectedSonosGroupSettings | None = None


class SonosPlayerSettings(PersistedSonosPlayerSettings):
    manual_host: str | None = None
    manual_name: str | None = None

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


class Pn532SpiSettings(StrictModel):
    reset: int | None = Field(default=None, ge=0)
    cs: int | None = Field(default=None, ge=0)
    irq: int | None = Field(default=None, ge=0)


class Pn532ReaderSettings(StrictModel):
    read_timeout_seconds: float = Field(default=0.1, gt=0)
    board_profile: Literal["waveshare_hat", "hiletgo_v3", "custom"] = "waveshare_hat"
    protocol: Literal["spi"] = "spi"
    spi: Pn532SpiSettings = Field(default_factory=Pn532SpiSettings)


class ReaderSettings(StrictModel):
    type: Literal["dryrun", "pn532"] = "dryrun"
    pn532: Pn532ReaderSettings = Field(default_factory=Pn532ReaderSettings)


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
    uid: str | None = None


class SparseSelectedSonosGroupSettings(StrictModel):
    household_id: str | None = None
    coordinator_uid: str | None = None
    members: list[SparseSelectedSonosSpeakerSettings] | None = None


class SparsePersistedSonosPlayerSettings(StrictModel):
    selected_group: SparseSelectedSonosGroupSettings | None = None


class SparseSonosPlayerSettings(SparsePersistedSonosPlayerSettings):
    manual_host: str | None = None
    manual_name: str | None = None


class SparsePersistedPlayerSettings(StrictModel):
    type: Literal["dryrun", "sonos"] | None = None
    sonos: SparsePersistedSonosPlayerSettings | None = None


class SparsePlayerSettings(SparsePersistedPlayerSettings):
    sonos: SparseSonosPlayerSettings | None = None


class SparsePn532SpiSettings(StrictModel):
    reset: int | None = Field(default=None, ge=0)
    cs: int | None = Field(default=None, ge=0)
    irq: int | None = Field(default=None, ge=0)


class SparsePn532ReaderSettings(StrictModel):
    read_timeout_seconds: float | None = None
    board_profile: Literal["waveshare_hat", "hiletgo_v3", "custom"] | None = None
    protocol: Literal["spi"] | None = None
    spi: SparsePn532SpiSettings | None = None


class SparseReaderSettings(StrictModel):
    type: Literal["dryrun", "pn532"] | None = None
    pn532: SparsePn532ReaderSettings | None = None


class SparsePlaybackSettings(StrictModel):
    pause_duration_seconds: int | None = None
    pause_delay_seconds: float | None = None


class SparseRuntimeSettings(StrictModel):
    loop_interval_seconds: float | None = None


class SparsePersistedJukeboxSettings(StrictModel):
    player: SparsePersistedPlayerSettings | None = None
    reader: SparseReaderSettings | None = None
    playback: SparsePlaybackSettings | None = None
    runtime: SparseRuntimeSettings | None = None


class SparseJukeboxSettings(SparsePersistedJukeboxSettings):
    player: SparsePlayerSettings | None = None


class SparseServerSettings(StrictModel):
    port: int | None = None


class SparsePathsSettings(StrictModel):
    library_path: str | None = None


class SparseAdminSettings(StrictModel):
    api: SparseServerSettings | None = None
    ui: SparseServerSettings | None = None


class SparsePersistedAppSettings(StrictModel):
    schema_version: int
    paths: SparsePathsSettings | None = None
    jukebox: SparsePersistedJukeboxSettings | None = None
    admin: SparseAdminSettings | None = None


class SparseAppSettings(SparsePersistedAppSettings):
    jukebox: SparseJukeboxSettings | None = None


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
    sonos_host: str | None = None
    sonos_name: str | None = None
    sonos_group: ResolvedSonosGroupRuntime | None = None
    reader_type: Literal["dryrun", "pn532"]
    pause_duration_seconds: int
    pause_delay_seconds: float
    loop_interval_seconds: float
    pn532_read_timeout_seconds: float
    pn532_board_profile: Literal["waveshare_hat", "hiletgo_v3", "custom"]
    pn532_protocol: Literal["spi"] = "spi"
    pn532_spi_reset: int | None
    pn532_spi_cs: int | None
    pn532_spi_irq: int | None
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
