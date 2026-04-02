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
        normalization_errors = []
        for speaker in available_speakers:
            normalized, error = self._normalize_speaker(speaker)
            if normalized is None:
                if error is not None:
                    normalization_errors.append(error)
                continue

            existing = speakers_by_uid.get(normalized.uid)
            speakers_by_uid[normalized.uid] = self._choose_preferred(existing, normalized)

        if not speakers_by_uid and normalization_errors:
            raise SonosDiscoveryError(
                f"Discovered Sonos speakers but failed to inspect any reachable speakers: {normalization_errors[0]}"
            )

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
    def _normalize_speaker(
        speaker: "_SonosSpeakerLike",
    ) -> tuple[Optional[DiscoveredSonosSpeaker], Optional[str]]:
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            return (
                DiscoveredSonosSpeaker(
                    uid=speaker.uid,
                    name=speaker.player_name,
                    host=speaker.ip_address,
                    household_id=speaker.household_id,
                    is_visible=getattr(speaker, "is_visible", True) is not False,
                ),
                None,
            )
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            return (
                None,
                "{}: {}".format(
                    _safe_speaker_identifier(speaker),
                    err,
                ),
            )


class _SonosSpeakerLike(Protocol):
    uid: str
    player_name: str
    ip_address: str
    household_id: str
    all_zones: set[Any]


def _safe_speaker_identifier(speaker: "_SonosSpeakerLike") -> str:
    ip_address = getattr(speaker, "ip_address", None)
    if ip_address:
        return str(ip_address)

    try:
        uid = getattr(speaker, "uid")
    except Exception:
        return "unknown speaker"

    return str(uid)
