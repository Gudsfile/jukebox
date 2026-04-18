import ipaddress
import re
import select
import socket
import struct
import time
from dataclasses import dataclass
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


_SSDP_RESPONSE_TIMEOUT_SECONDS = 1.0
_SSDP_RESPONSE_POLL_INTERVAL_SECONDS = 0.1
_SSDP_MULTICAST_GROUP = "239.255.255.250"
_SSDP_MULTICAST_PORT = 1900
_HOUSEHOLD_HEADER_RE = re.compile(rb"(?im)^x-rincon-household:\s*([^\r\n]+)")
_PLAYER_SEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {_SSDP_MULTICAST_GROUP}:{_SSDP_MULTICAST_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 1\r\n"
    "ST: urn:schemas-upnp-org:device:ZonePlayer:1\r\n"
    "\r\n"
).encode("utf-8")


class SoCoSonosDiscoveryAdapter(SonosDiscoveryPort):
    def discover_speakers(self) -> list[DiscoveredSonosSpeaker]:
        snapshot = self._discover_network_snapshot()
        return self._recover_snapshot_speakers(snapshot)

    def discover_household_speakers(self, household_id: str) -> list[DiscoveredSonosSpeaker]:
        snapshot = self._discover_household_snapshot(household_id)
        return sort_sonos_speakers(
            [speaker for speaker in self._recover_snapshot_speakers(snapshot) if speaker.household_id == household_id]
        )

    def _recover_snapshot_speakers(self, snapshot: _SonosDiscoverySnapshot) -> list[DiscoveredSonosSpeaker]:
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

    def _discover_network_snapshot(self) -> _SonosDiscoverySnapshot:
        import soco
        import soco.discovery
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException
        from urllib3.exceptions import HTTPError

        try:
            discovered = self._discover_multicast_network_speakers()
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err

        if not discovered:
            try:
                discovered = soco.discovery.scan_network(
                    include_invisible=True,
                    multi_household=True,
                    networks_to_scan=_build_private_ipv4_networks_to_scan(),
                )
            except (HTTPError, OSError, RequestException, SoCoException) as err:
                raise SonosDiscoveryError(f"Failed to discover Sonos speakers: {err}") from err
        return self._normalize_snapshot(set(discovered or set()))

    def _discover_household_snapshot(self, household_id: str) -> _SonosDiscoverySnapshot:
        import soco
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException
        from urllib3.exceptions import HTTPError

        try:
            discovered = soco.discover(
                include_invisible=True,
                household_id=household_id,
                allow_network_scan=True,
                networks_to_scan=_build_private_ipv4_networks_to_scan(),
            )
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise SonosDiscoveryError(f"Failed to discover Sonos household `{household_id}`: {err}") from err

        snapshot = self._normalize_snapshot(set(discovered or set()))
        return _SonosDiscoverySnapshot(
            speakers=[speaker for speaker in snapshot.speakers if speaker.household_id == household_id],
            retry_hosts_by_uid=snapshot.retry_hosts_by_uid,
            normalization_errors=snapshot.normalization_errors,
        )

    def _discover_multicast_network_speakers(self) -> set[Any]:
        import soco
        import soco.discovery
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        interface_addresses = soco.discovery._find_ipv4_addresses()
        if not interface_addresses:
            return set()

        sockets = []
        for interface_address in interface_addresses:
            try:
                multicast_socket = self._create_multicast_socket(interface_address)
            except OSError:
                continue
            sockets.append(multicast_socket)

        if not sockets:
            return set()

        try:
            for _ in range(3):
                for multicast_socket in list(sockets):
                    try:
                        multicast_socket.sendto(_PLAYER_SEARCH, (_SSDP_MULTICAST_GROUP, _SSDP_MULTICAST_PORT))
                    except OSError:
                        sockets.remove(multicast_socket)
                        multicast_socket.close()

            if not sockets:
                return set()

            household_hosts = self._collect_multicast_household_hosts(sockets)
        finally:
            for multicast_socket in sockets:
                multicast_socket.close()

        speakers = set()
        for hosts in household_hosts.values():
            for host in hosts:
                try:
                    speakers.update(soco.SoCo(host).all_zones)
                    break
                except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException):
                    continue
        return speakers

    @staticmethod
    def _create_multicast_socket(interface_address: str) -> socket.socket:
        multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", 4))
        multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface_address))
        return multicast_socket

    def _collect_multicast_household_hosts(self, sockets: list[socket.socket]) -> dict[str, list[str]]:
        deadline = time.monotonic() + _SSDP_RESPONSE_TIMEOUT_SECONDS
        household_hosts = {}

        while sockets:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            ready_sockets, _, _ = select.select(
                sockets,
                [],
                [],
                min(remaining, _SSDP_RESPONSE_POLL_INTERVAL_SECONDS),
            )
            if not ready_sockets:
                continue

            for ready_socket in ready_sockets:
                response, address = ready_socket.recvfrom(1024)
                household_id = _extract_sonos_household_id(response)
                if household_id is None:
                    continue
                hosts = household_hosts.setdefault(household_id, [])
                if address[0] not in hosts:
                    hosts.append(address[0])

        return household_hosts

    def _normalize_snapshot(self, discovered: set[Any]) -> _SonosDiscoverySnapshot:
        normalization_errors = []
        available_speakers = set(discovered)
        for speaker in list(discovered):
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


def _extract_sonos_household_id(response: bytes) -> Optional[str]:
    match = _HOUSEHOLD_HEADER_RE.search(response)
    if match is None:
        return None
    return match.group(1).decode("utf-8", "ignore").strip() or None


def _build_private_ipv4_networks_to_scan() -> list[str]:
    import ifaddr

    networks = set()
    for adapter in ifaddr.get_adapters():
        for adapter_ip in adapter.ips:
            try:
                ipv4_address = ipaddress.IPv4Address(adapter_ip.ip)
            except Exception:
                continue

            if adapter_ip.network_prefix >= 32:
                continue

            ipv4_network = ipaddress.ip_network(f"{ipv4_address}/{adapter_ip.network_prefix}", strict=False)
            if not ipv4_network.is_private or ipv4_network.is_loopback or ipv4_network.is_link_local:
                continue
            networks.add(str(ipv4_network))

    return sorted(networks)
