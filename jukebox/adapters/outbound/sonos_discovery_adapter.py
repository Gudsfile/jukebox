from typing import Any, Optional, Protocol

from jukebox.sonos.discovery import (
    DiscoveredSonosSpeaker,
    SonosDiscoveryError,
    SonosDiscoveryPort,
    SonosDiscoverySnapshot,
    sort_sonos_speakers,
)


class SoCoSonosDiscoveryAdapter(SonosDiscoveryPort):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]:
        snapshot = self.discover_runtime_snapshot()
        if not snapshot.speakers and snapshot.normalization_errors:
            raise SonosDiscoveryError(
                "Discovered Sonos speakers but failed to inspect any reachable speakers: "
                f"{snapshot.normalization_errors[0]}"
            )
        return snapshot.speakers

    def discover_runtime_snapshot(self) -> SonosDiscoverySnapshot:
        import soco
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException
        from urllib3.exceptions import HTTPError

        try:
            discovered = soco.discover()
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err

        if not discovered:
            return SonosDiscoverySnapshot(
                speakers=[],
                retry_hosts_by_uid={},
                normalization_errors=[],
            )

        available_speakers = set(discovered)
        for speaker in list(discovered):
            try:
                available_speakers.update(speaker.all_zones)
            except Exception:
                available_speakers.add(speaker)

        speakers_by_uid = {}
        retry_hosts_by_uid = {}
        normalization_errors = []
        for speaker in available_speakers:
            expected_uid = _safe_speaker_uid(speaker)
            normalized, error = self._normalize_speaker(speaker)
            if normalized is None:
                if error is not None:
                    normalization_errors.append(error)
                if expected_uid is not None:
                    host = _safe_speaker_host(speaker)
                    if host is not None:
                        retry_hosts_by_uid.setdefault(expected_uid, set()).add(host)
                continue

            existing = speakers_by_uid.get(normalized.uid)
            speakers_by_uid[normalized.uid] = self._choose_preferred(existing, normalized)

        return SonosDiscoverySnapshot(
            speakers=sort_sonos_speakers(list(speakers_by_uid.values())),
            retry_hosts_by_uid={uid: sorted(hosts) for uid, hosts in sorted(retry_hosts_by_uid.items())},
            normalization_errors=normalization_errors,
        )

    def resolve_speaker_by_host(self, expected_uid: str, host: str) -> DiscoveredSonosSpeaker:
        from requests.exceptions import RequestException
        from soco import SoCo
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            speaker = SoCo(host)
            resolved_uid = speaker.uid
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise ValueError(f"Failed to contact saved Sonos speaker at {host}: {err}") from err

        if resolved_uid != expected_uid:
            raise ValueError(
                f"Saved Sonos speaker UID mismatch for host {host}: expected {expected_uid}, resolved {resolved_uid}"
            )

        try:
            return DiscoveredSonosSpeaker(
                uid=speaker.uid,
                name=speaker.player_name,
                host=speaker.ip_address,
                household_id=speaker.household_id,
                is_visible=getattr(speaker, "is_visible", True) is not False,
            )
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise ValueError(f"Failed to inspect discovered Sonos speaker at {host}: {err}") from err

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
    ip_address = _safe_speaker_host(speaker)
    if ip_address:
        return ip_address

    try:
        uid = getattr(speaker, "uid")
    except Exception:
        return "unknown speaker"

    return str(uid)


def _safe_speaker_host(speaker: "_SonosSpeakerLike") -> Optional[str]:
    try:
        ip_address = getattr(speaker, "ip_address", None)
    except Exception:
        return None

    if ip_address:
        return str(ip_address)
    return None


def _safe_speaker_uid(speaker: "_SonosSpeakerLike") -> Optional[str]:
    try:
        return str(getattr(speaker, "uid"))
    except Exception:
        return None
