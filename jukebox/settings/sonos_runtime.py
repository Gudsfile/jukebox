from typing import Any, Protocol

from .entities import (
    ResolvedSonosGroupRuntime,
    ResolvedSonosSpeakerRuntime,
    SelectedSonosGroupSettings,
)


class SonosGroupResolver(Protocol):
    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime: ...


class SoCoSonosGroupResolver:
    def resolve_selected_group(
        self,
        selected_group: SelectedSonosGroupSettings,
    ) -> ResolvedSonosGroupRuntime:
        import soco
        from soco import SoCo

        available_speakers = self._discover_available_speakers(soco)
        resolved_members = []
        member_resolution_errors = []

        for saved_member in selected_group.members:
            runtime_member = None
            resolved_speaker = available_speakers.get(saved_member.uid)

            if resolved_speaker is not None:
                try:
                    runtime_member = self._build_runtime_speaker(resolved_speaker)
                except ValueError:
                    runtime_member = None

            if runtime_member is None:
                host_candidates = []
                if resolved_speaker is not None and resolved_speaker.ip_address:
                    host_candidates.append(resolved_speaker.ip_address)
                if saved_member.last_known_host is not None and saved_member.last_known_host not in host_candidates:
                    host_candidates.append(saved_member.last_known_host)

                host_errors = []
                for host in host_candidates:
                    try:
                        resolved_speaker = self._resolve_by_host(SoCo, saved_member.uid, host)
                        runtime_member = self._build_runtime_speaker(resolved_speaker)
                        break
                    except ValueError as err:
                        host_errors.append(f"{saved_member.uid} via {host}: {err}")

                if runtime_member is None and host_errors:
                    member_resolution_errors.append("; ".join(host_errors))
                    continue

            if runtime_member is None:
                if saved_member.last_known_host is None:
                    member_resolution_errors.append(
                        f"{saved_member.uid}: not found on network and has no last_known_host"
                    )
                else:
                    member_resolution_errors.append(
                        f"{saved_member.uid} via {saved_member.last_known_host}: not reachable"
                    )
                continue

            resolved_members.append(runtime_member)

        if member_resolution_errors:
            details = "; ".join(sorted(member_resolution_errors))
            raise ValueError(f"Unable to resolve saved Sonos speaker(s): {details}")

        coordinator = next(
            (member for member in resolved_members if member.uid == selected_group.coordinator_uid),
            None,
        )
        if coordinator is None:
            raise ValueError("Saved Sonos coordinator did not resolve to one of the selected_group members")

        household_ids = {member.household_id for member in resolved_members}
        if len(household_ids) != 1:
            raise ValueError("Resolved Sonos group members must belong to the same household")

        if selected_group.household_id is not None and selected_group.household_id not in household_ids:
            raise ValueError("Resolved Sonos group household does not match the saved selected_group household_id")

        return ResolvedSonosGroupRuntime(
            household_id=coordinator.household_id,
            coordinator=coordinator,
            members=resolved_members,
        )

    @staticmethod
    def _discover_available_speakers(soco_module: Any) -> dict[str, "_SonosSpeakerLike"]:
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            discovered = soco_module.discover()
        except (HTTPError, OSError, RequestException, SoCoException) as err:
            raise ValueError(f"Failed to discover Sonos speakers: {err}") from err

        if not discovered:
            return {}

        available_speakers = set(discovered)
        for speaker in list(discovered):
            try:
                available_speakers.update(speaker.all_zones)
            except Exception:
                available_speakers.add(speaker)

        speakers_by_uid = {}
        for speaker in available_speakers:
            try:
                speakers_by_uid[speaker.uid] = speaker
            except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException):
                continue

        return speakers_by_uid

    @staticmethod
    def _resolve_by_host(SoCo: Any, expected_uid: str, host: str) -> "_SonosSpeakerLike":
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            speaker = SoCo(host)
            resolved_uid = speaker.uid
        except (HTTPError, OSError, RequestException, SoCoException, SoCoUPnPException) as err:
            raise ValueError(f"Failed to contact saved Sonos speaker at {host}: {err}") from err

        if resolved_uid != expected_uid:
            raise ValueError(
                f"Saved Sonos speaker UID mismatch for host {host}: expected {expected_uid}, resolved {resolved_uid}"
            )
        return speaker

    @staticmethod
    def _build_runtime_speaker(speaker: "_SonosSpeakerLike") -> ResolvedSonosSpeakerRuntime:
        from requests.exceptions import RequestException
        from soco.exceptions import SoCoException, SoCoUPnPException
        from urllib3.exceptions import HTTPError

        try:
            return ResolvedSonosSpeakerRuntime(
                uid=speaker.uid,
                name=speaker.player_name,
                host=speaker.ip_address,
                household_id=speaker.household_id,
            )
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise ValueError(f"Failed to inspect discovered Sonos speaker at {speaker.ip_address}: {err}") from err


class _SonosSpeakerLike(Protocol):
    uid: str
    player_name: str
    ip_address: str
    household_id: str
    all_zones: set[Any]
