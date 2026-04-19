from dataclasses import dataclass

from jukebox.sonos.discovery import DiscoveredSonosSpeaker, sort_sonos_speakers


@dataclass(frozen=True)
class GroupedSonosHousehold:
    household_id: str
    speakers: tuple[DiscoveredSonosSpeaker, ...]


def group_sonos_speakers_by_household(speakers: list[DiscoveredSonosSpeaker]) -> list[GroupedSonosHousehold]:
    speakers_by_household = {}
    for speaker in sort_sonos_speakers(speakers):
        speakers_by_household.setdefault(speaker.household_id, []).append(speaker)

    households = [
        GroupedSonosHousehold(
            household_id=household_id,
            speakers=tuple(members),
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
