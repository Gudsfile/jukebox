from typing import Protocol

from pydantic import BaseModel, ConfigDict


class DiscoveredSonosSpeaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uid: str
    name: str
    host: str
    household_id: str
    is_visible: bool


class DiscoveredSonosHousehold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    household_id: str
    speakers: list[DiscoveredSonosSpeaker]


class SonosDiscoveryError(RuntimeError, ValueError):
    pass


class SonosDiscoveryPort(Protocol):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]: ...


def sort_sonos_speakers(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosSpeaker]:
    return sorted(speakers, key=lambda speaker: (speaker.name, speaker.host, speaker.uid))


def group_sonos_speakers_by_household(speakers: list[DiscoveredSonosSpeaker]) -> list[DiscoveredSonosHousehold]:
    speakers_by_household = {}
    for speaker in sort_sonos_speakers(speakers):
        speakers_by_household.setdefault(speaker.household_id, []).append(speaker)

    households = [
        DiscoveredSonosHousehold(
            household_id=household_id,
            speakers=members,
        )
        for household_id, members in speakers_by_household.items()
    ]
    return sorted(
        households,
        key=lambda household: (
            household.speakers[0].name if household.speakers else "",
            household.speakers[0].host if household.speakers else "",
            household.household_id,
        ),
    )
