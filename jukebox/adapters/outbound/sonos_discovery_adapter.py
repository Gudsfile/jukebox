import select
import socket
import struct
import time
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Optional, Protocol

from jukebox.sonos.discovery import (
    DiscoveredSonosSpeaker,
    SonosDiscoveryError,
    SonosDiscoveryPort,
    sort_sonos_speakers,
)


@dataclass(frozen=True)
class _SonosDiscoverySnapshot:
    speakers: list[DiscoveredSonosSpeaker]
    retry_hosts_by_uid: dict[str, list[str]]
    normalization_errors: list[str]


class SoCoSonosDiscoveryAdapter(SonosDiscoveryPort):
    def discover_speakers(self, include_other_households: bool = False) -> list[DiscoveredSonosSpeaker]:
        snapshot = self._discover_runtime_snapshot(include_other_households=include_other_households)
        speakers_by_uid = {speaker.uid: speaker for speaker in snapshot.speakers}
        for expected_uid, hosts in snapshot.retry_hosts_by_uid.items():
            for host in hosts:
                try:
                    recovered = self._resolve_speaker_by_host(expected_uid, host)
                except ValueError:
                    continue

                existing = speakers_by_uid.get(recovered.uid)
                speakers_by_uid[recovered.uid] = self._choose_preferred(existing, recovered)
                break

        recovered_speakers = sort_sonos_speakers(list(speakers_by_uid.values()))
        if not recovered_speakers and snapshot.normalization_errors:
            raise SonosDiscoveryError(
                "Discovered Sonos speakers but failed to inspect any reachable speakers: "
                f"{snapshot.normalization_errors[0]}"
            )
        return recovered_speakers

    def _discover_runtime_snapshot(self, include_other_households: bool = False) -> _SonosDiscoverySnapshot:
        import soco
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException
        from urllib3.exceptions import HTTPError

        try:
            discovered = soco.discover()
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err

        discovered = set(discovered or set())
        normalization_errors = []
        responder_hosts = set()
        if include_other_households or not discovered:
            try:
                responder_hosts = self._discover_responder_hosts()
            except OSError as err:
                if not discovered:
                    raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err
                normalization_errors.append(f"Failed to inspect Sonos SSDP responders: {err}")

        available_speakers = set(discovered)
        for speaker in list(discovered):
            try:
                available_speakers.update(speaker.all_zones)
            except Exception:
                available_speakers.add(speaker)

        for host in sorted(responder_hosts):
            try:
                speaker = soco.SoCo(host)
            except (HTTPError, OSError, RequestException, RuntimeError, SoCoException) as err:
                normalization_errors.append(f"{host}: {err}")
                continue

            available_speakers.add(speaker)
            try:
                available_speakers.update(speaker.all_zones)
            except Exception:
                available_speakers.add(speaker)

        if not available_speakers:
            return _SonosDiscoverySnapshot(
                speakers=[],
                retry_hosts_by_uid={},
                normalization_errors=normalization_errors,
            )

        speakers_by_uid = {}
        retry_hosts_by_uid = {}
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

        return _SonosDiscoverySnapshot(
            speakers=sort_sonos_speakers(list(speakers_by_uid.values())),
            retry_hosts_by_uid={uid: sorted(hosts) for uid, hosts in sorted(retry_hosts_by_uid.items())},
            normalization_errors=normalization_errors,
        )

    @staticmethod
    def _discover_responder_hosts(timeout: float = 1.0) -> set[str]:
        try:
            from importlib import import_module

            soco_discovery = import_module("soco.discovery")
        except ImportError:
            return set()

        responder_hosts = set()
        interface_addresses = soco_discovery._find_ipv4_addresses()
        if not interface_addresses:
            return responder_hosts

        payload = dedent(
            """\
            M-SEARCH * HTTP/1.1
            HOST: 239.255.255.250:1900
            MAN: "ssdp:discover"
            MX: 1
            ST: urn:schemas-upnp-org:device:ZonePlayer:1
            """
        ).encode("utf-8")

        sockets = []
        try:
            for address in interface_addresses:
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 4))
                    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(address))
                except OSError:
                    if sock is not None:
                        sock.close()
                    continue
                sockets.append(sock)

            for _ in range(3):
                for sock in list(sockets):
                    try:
                        sock.sendto(payload, ("239.255.255.250", 1900))
                    except OSError:
                        sockets.remove(sock)
                        sock.close()

            deadline = time.time() + timeout
            while sockets and time.time() < deadline:
                readable, _, _ = select.select(sockets, [], [], min(0.1, max(deadline - time.time(), 0.0)))
                if not readable:
                    continue

                for sock in readable:
                    try:
                        data, addr = sock.recvfrom(1024)
                    except OSError:
                        continue
                    if b"Sonos" not in data:
                        continue
                    responder_hosts.add(addr[0])
        finally:
            for sock in sockets:
                sock.close()

        return responder_hosts

    def _resolve_speaker_by_host(self, expected_uid: str, host: str) -> DiscoveredSonosSpeaker:
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
                f"{_safe_speaker_identifier(speaker)}: {err}",
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
