from typing import TYPE_CHECKING, Literal, Optional, Protocol

from pydantic import BaseModel, ConfigDict, model_validator

if TYPE_CHECKING:
    from jukebox.settings.entities import SelectedSonosGroupSettings


class DiscoveredSonosSpeaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uid: str
    name: str
    host: str
    household_id: str
    is_visible: bool


class SonosDiscoveryError(RuntimeError, ValueError):
    pass


class SonosDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["current_household", "all_households", "target_household"] = "current_household"
    household_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_request(self):
        if self.mode == "target_household":
            if not self.household_id:
                raise ValueError("target_household discovery requires household_id")
            return self

        if self.household_id is not None:
            raise ValueError("household_id is only valid for target_household discovery")
        return self

    @classmethod
    def current_household(cls) -> "SonosDiscoveryRequest":
        return cls(mode="current_household")

    @classmethod
    def all_households(cls) -> "SonosDiscoveryRequest":
        return cls(mode="all_households")

    @classmethod
    def target_household(cls, household_id: str) -> "SonosDiscoveryRequest":
        return cls(mode="target_household", household_id=household_id)


class SonosDiscoveryPort(Protocol):
    def discover_speakers(
        self,
        request: Optional[SonosDiscoveryRequest] = None,
    ) -> list[DiscoveredSonosSpeaker]: ...

    def resolve_group_members(
        self,
        selected_group: "SelectedSonosGroupSettings",
    ) -> list[DiscoveredSonosSpeaker]: ...


def sort_sonos_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
    return sorted(speakers, key=lambda speaker: (speaker.name, speaker.host, speaker.uid))
