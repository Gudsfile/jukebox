from typing import Any, Optional, Protocol

from jukebox.sonos.discovery import (
    DiscoveredSonosSpeaker,
    SonosDiscoveryError,
    SonosDiscoveryPort,
    sort_sonos_speakers,
)


class SoCoSonosDiscoveryAdapter(SonosDiscoveryPort):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]:
        import soco
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException
        from urllib3.exceptions import HTTPError

        try:
            discovered = soco.discover()
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err

        if not discovered:
            return []

        available_speakers = set(discovered)
        for speaker in list(discovered):
            try:
                available_speakers.update(speaker.all_zones)
            except Exception:
                available_speakers.add(speaker)

        speakers_by_uid = {}
        for speaker in available_speakers:
            normalized = self._normalize_speaker(speaker)
            if normalized is None:
                continue

            existing = speakers_by_uid.get(normalized.uid)
            speakers_by_uid[normalized.uid] = self._choose_preferred(existing, normalized)

        return sort_sonos_speakers(list(speakers_by_uid.values()))

    @staticmethod
    def _choose_preferred(
        existing: Optional[DiscoveredSonosSpeaker],
        candidate: DiscoveredSonosSpeaker,
    ) -> DiscoveredSonosSpeaker:
        if existing is None:
            return candidate
        if candidate.is_visible and not existing.is_visible:
            return candidate
        if existing.is_visible and not candidate.is_visible:
            return existing
        if (candidate.name, candidate.host, candidate.uid) < (existing.name, existing.host, existing.uid):
            return candidate
        return existing

    @staticmethod
    def _normalize_speaker(speaker: "_SonosSpeakerLike") -> Optional[DiscoveredSonosSpeaker]:
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            return DiscoveredSonosSpeaker(
                uid=speaker.uid,
                name=speaker.player_name,
                host=speaker.ip_address,
                household_id=speaker.household_id,
                is_visible=getattr(speaker, "is_visible", True) is not False,
            )
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException):
            return None


class _SonosSpeakerLike(Protocol):
    uid: str
    player_name: str
    ip_address: str
    household_id: str
    all_zones: set[Any]
