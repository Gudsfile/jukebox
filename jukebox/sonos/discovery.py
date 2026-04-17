from typing import Literal, Optional, Protocol

from pydantic import BaseModel, ConfigDict, model_validator


class DiscoveredSonosSpeaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uid: str
    name: str
    host: str
    household_id: str
    is_visible: bool


class SonosDiscoveryError(RuntimeError, ValueError):
    pass


class SonosDiscoveryScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["all_network", "household"] = "all_network"
    household_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.mode == "household":
            if not self.household_id:
                raise ValueError("household discovery requires household_id")
            return self

        if self.household_id is not None:
            raise ValueError("household_id is only valid for household-scoped discovery")
        return self

    @classmethod
    def all_network(cls) -> "SonosDiscoveryScope":
        return cls(mode="all_network")

    @classmethod
    def household(cls, household_id: str) -> "SonosDiscoveryScope":
        return cls(mode="household", household_id=household_id)


class SonosDiscoveryPort(Protocol):
    def discover_speakers(
        self,
        scope: Optional[SonosDiscoveryScope] = None,
    ) -> list[DiscoveredSonosSpeaker]: ...


def sort_sonos_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
    return sorted(speakers, key=lambda speaker: (speaker.name, speaker.host, speaker.uid))
