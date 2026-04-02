from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class DiscoveredSonosSpeaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uid: str
    name: str
    host: str
    household_id: str
    is_visible: bool


class SonosDiscoveryError(RuntimeError, ValueError):
    pass


@dataclass(frozen=True)
class SonosDiscoverySnapshot:
    speakers: list[DiscoveredSonosSpeaker]
    retry_hosts_by_uid: dict[str, list[str]]
    normalization_errors: list[str]


class SonosDiscoveryPort(Protocol):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]: ...

    def discover_runtime_snapshot(self) -> SonosDiscoverySnapshot: ...

    def resolve_speaker_by_host(self, expected_uid: str, host: str) -> DiscoveredSonosSpeaker: ...


def sort_sonos_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
    return sorted(speakers, key=lambda speaker: (speaker.name, speaker.host, speaker.uid))
