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


class SonosDiscoveryPort(Protocol):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]: ...


def sort_sonos_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
    return sorted(speakers, key=lambda speaker: (speaker.name, speaker.host, speaker.uid))
