import logging
from collections.abc import Callable

import soco
from requests.exceptions import RequestException
from soco import SoCo
from soco.exceptions import SoCoException, SoCoUPnPException
from soco.plugins.sharelink import ShareLinkPlugin
from urllib3.exceptions import HTTPError

from jukebox.domain.errors import PlaybackError
from jukebox.domain.ports import PlayerPort
from jukebox.settings.entities import (
    ResolvedSonosGroupRuntime,
    SelectedSonosGroupSettings,
    SelectedSonosSpeakerSettings,
)
from jukebox.settings.errors import InvalidSettingsError
from jukebox.sonos.service import SonosGroupResolver

LOGGER = logging.getLogger("jukebox")
_SONOS_TRANSPORT_ERRORS = (HTTPError, OSError, RequestException, SoCoException)


def _log_upnp_failure(command_name: str, err: SoCoUPnPException) -> None:
    if "UPnP Error 804" in str(err.message):
        LOGGER.warning("%s failed, probably a bad uri: %s", command_name, err.message)
    elif "UPnP Error 701" in str(err.message):
        LOGGER.warning(
            "%s failed, probably a not available transition: %s",
            command_name,
            err.message,
        )
    else:
        LOGGER.exception("%s failed: %s", command_name, str(err))


def catch_soco_upnp_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SoCoUPnPException as err:
            _log_upnp_failure(func.__name__, err)
            raise PlaybackError(str(err)) from err

    return wrapper


class SonosPlayerAdapter(PlayerPort):
    """Adapter for Sonos player implementing PlayerPort."""

    def __init__(
        self,
        host: str | None = None,
        name: str | None = None,
        group: ResolvedSonosGroupRuntime | None = None,
        sonos_group_resolver: SonosGroupResolver | None = None,
    ):
        self.manual_name = name
        self.group = group
        self.selected_group = _selected_group_from_runtime_group(group)
        self.sonos_group_resolver = sonos_group_resolver
        self.speaker_name = "unknown Sonos player"

        try:
            if group is not None:
                coordinator_host = host or group.coordinator.host
                self.speaker = SoCo(coordinator_host)
                # Apply the saved selection once at startup. Later regrouping in the
                # Sonos app is intentionally left alone until jukebox restarts.
                self._enforce_group(group)
            elif host:
                self.speaker = SoCo(host)
            else:
                self.speaker = self._discover(name)

            speaker_info = self._refresh_speaker_metadata()
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise InvalidSettingsError(f"Failed to initialize Sonos player: {err}") from err

        LOGGER.info(
            "Found `%s` with software version: %s",
            self.speaker_name,
            speaker_info.get("software_version", None),
        )
        self.sharelink = ShareLinkPlugin(self.speaker)

    @staticmethod
    def _discover(name: str | None = None) -> SoCo:
        discovered = soco.discover()
        if not discovered:
            raise RuntimeError("No Sonos speakers found on the network")
        speakers = sorted(discovered, key=lambda s: s.player_name)
        LOGGER.info("Discovered %d Sonos speaker(s): %s", len(speakers), [s.player_name for s in speakers])
        if name:
            matching = [s for s in speakers if s.player_name == name]
            if len(matching) > 1:
                LOGGER.warning(
                    "Multiple Sonos speakers with name '%s' found. Using first match. "
                    "Consider using host IP to disambiguate.",
                    name,
                )
            if matching:
                return matching[0]
            raise RuntimeError(f"No Sonos speaker named '{name}' found on the network")
        return speakers[0]

    def _enforce_group(self, group: ResolvedSonosGroupRuntime) -> None:
        desired_member_uids = group.desired_member_uids
        speakers_by_uid = {member.uid: SoCo(member.host) for member in group.members}
        coordinator = speakers_by_uid[group.coordinator.uid]
        applied_operations = []

        if group.is_partial:
            LOGGER.warning("Applying Sonos group best-effort with missing saved members: %s", group.missing_member_uids)

        try:
            for member in group.members:
                if member.uid == group.coordinator.uid:
                    continue

                speaker = speakers_by_uid[member.uid]
                if self._is_joined_to_coordinator(speaker, coordinator):
                    continue

                rollback_coordinator = self._get_rollback_coordinator_for_join(speaker)
                LOGGER.info(
                    "Joining Sonos speaker `%s` to `%s` before playback",
                    speaker.player_name,
                    coordinator.player_name,
                )
                speaker.join(coordinator)
                applied_operations.append(("join", speaker, rollback_coordinator))

            current_group = coordinator.group
            if current_group is not None:
                for current_member in list(current_group.members):
                    if current_member.uid in desired_member_uids or self._is_nonstandalone_group_member(current_member):
                        continue

                    LOGGER.info(
                        "Removing Sonos speaker `%s` from coordinator group before playback",
                        current_member.player_name,
                    )
                    current_member.unjoin()
                    applied_operations.append(("unjoin", current_member, None))
        except Exception:
            self._rollback_group_changes(applied_operations, coordinator)
            raise

    def _rollback_group_changes(self, applied_operations, coordinator: SoCo) -> None:
        for operation, speaker, rollback_target in reversed(applied_operations):
            try:
                if operation == "join":
                    LOGGER.warning(
                        "Rolling back Sonos join for `%s` after startup group enforcement failed",
                        speaker.player_name,
                    )
                    if rollback_target is None:
                        speaker.unjoin()
                    else:
                        speaker.join(rollback_target)
                else:
                    LOGGER.warning(
                        "Rolling back Sonos removal for `%s` after startup group enforcement failed",
                        speaker.player_name,
                    )
                    speaker.join(coordinator)
            except Exception as err:
                LOGGER.warning(
                    "Failed to roll back Sonos group change `%s` for `%s`: %s",
                    operation,
                    speaker.player_name,
                    err,
                )

    @staticmethod
    def _is_joined_to_coordinator(speaker: SoCo, coordinator: SoCo) -> bool:
        current_group = speaker.group
        if current_group is None:
            return False

        current_coordinator = current_group.coordinator
        if current_coordinator is None:
            return False

        return current_coordinator.uid == coordinator.uid

    @staticmethod
    def _is_nonstandalone_group_member(speaker: SoCo) -> bool:
        return getattr(speaker, "is_visible", True) is False

    @staticmethod
    def _get_rollback_coordinator_for_join(speaker: SoCo) -> SoCo | None:
        current_group = speaker.group
        if current_group is None:
            return None

        current_coordinator = current_group.coordinator
        if current_coordinator is None or current_coordinator.uid == speaker.uid:
            return None

        return current_coordinator

    def _refresh_speaker_metadata(self) -> dict:
        speaker_info = self.speaker.get_speaker_info()
        self.speaker_name = self._speaker_name_from_info(speaker_info)
        if self.selected_group is None:
            self.selected_group = self._selected_group_from_current_speaker()
        return speaker_info

    def _speaker_name_from_info(self, speaker_info: dict) -> str:
        zone_name = speaker_info.get("zone_name")
        if isinstance(zone_name, str) and zone_name:
            return zone_name

        player_name = getattr(self.speaker, "player_name", None)
        if isinstance(player_name, str) and player_name:
            return player_name

        return "unknown Sonos player"

    def _selected_group_from_current_speaker(self) -> SelectedSonosGroupSettings | None:
        uid = getattr(self.speaker, "uid", None)
        household_id = getattr(self.speaker, "household_id", None)
        if not isinstance(uid, str) or not uid:
            return None
        if not isinstance(household_id, str) or not household_id:
            return None

        return SelectedSonosGroupSettings(
            household_id=household_id,
            coordinator_uid=uid,
            members=[SelectedSonosSpeakerSettings(uid=uid)],
        )

    def _execute_with_recovery(self, command_name: str, command: Callable[[], None]) -> None:
        try:
            command()
            return
        except SoCoUPnPException as err:
            _log_upnp_failure(command_name, err)
            raise PlaybackError(str(err)) from err
        except _SONOS_TRANSPORT_ERRORS as err:
            LOGGER.warning("%s failed for Sonos player `%s`: %s", command_name, self.speaker_name, err)
            original_error = err

        if not self._recover_speaker(command_name):
            raise PlaybackError(str(original_error)) from original_error

        try:
            command()
        except SoCoUPnPException as err:
            _log_upnp_failure(command_name, err)
            raise PlaybackError(str(err)) from err
        except _SONOS_TRANSPORT_ERRORS as err:
            LOGGER.warning("%s failed after Sonos recovery for `%s`: %s", command_name, self.speaker_name, err)
            raise PlaybackError(str(err)) from err

    def _recover_speaker(self, command_name: str) -> bool:
        if self.selected_group is not None:
            return self._recover_selected_group(command_name)

        if self.manual_name is not None:
            return self._recover_by_name(command_name)

        LOGGER.warning("%s could not recover Sonos player because no rediscoverable target is available", command_name)
        return False

    def _recover_selected_group(self, command_name: str) -> bool:
        assert self.selected_group is not None
        if self.sonos_group_resolver is None:
            LOGGER.warning(
                "%s could not re-resolve Sonos player `%s` because no Sonos group resolver is configured",
                command_name,
                self.speaker_name,
            )
            return False

        try:
            resolved_group = self.sonos_group_resolver.resolve_selected_group(self.selected_group)
            self._switch_to_resolved_group(resolved_group)
        except (
            HTTPError,
            OSError,
            RequestException,
            RuntimeError,
            ValueError,
            SoCoException,
            SoCoUPnPException,
        ) as err:
            LOGGER.warning("%s could not re-resolve Sonos player `%s`: %s", command_name, self.speaker_name, err)
            return False

        LOGGER.info(
            "%s recovered Sonos player `%s` at `%s`",
            command_name,
            self.speaker_name,
            resolved_group.coordinator.host,
        )
        return True

    def _switch_to_resolved_group(self, resolved_group: ResolvedSonosGroupRuntime) -> None:
        enforce_group = self.group is not None
        self.speaker = SoCo(resolved_group.coordinator.host)
        if enforce_group:
            self._enforce_group(resolved_group)
            self.group = resolved_group
        self.selected_group = _selected_group_from_runtime_group(resolved_group)
        self._refresh_speaker_metadata()
        self.sharelink = ShareLinkPlugin(self.speaker)

    def _recover_by_name(self, command_name: str) -> bool:
        try:
            self.speaker = self._discover(self.manual_name)
            self._refresh_speaker_metadata()
            self.sharelink = ShareLinkPlugin(self.speaker)
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            LOGGER.warning("%s could not rediscover Sonos player named `%s`: %s", command_name, self.manual_name, err)
            return False

        LOGGER.info("%s rediscovered Sonos player `%s`", command_name, self.speaker_name)
        return True

    def play(self, uri: str, shuffle: bool = False) -> None:
        def command() -> None:
            LOGGER.info("Playing `%s` on the player `%s`", uri, self.speaker_name)
            self.speaker.clear_queue()
            _ = self.handle_uri(uri)
            self.speaker.play_mode = "SHUFFLE_NOREPEAT" if shuffle else "NORMAL"
            self.speaker.play_from_queue(index=0, start=True)

        self._execute_with_recovery("play", command)

    def pause(self) -> None:
        def command() -> None:
            LOGGER.info("Pausing player `%s`", self.speaker_name)
            self.speaker.pause()

        self._execute_with_recovery("pause", command)

    def resume(self) -> None:
        def command() -> None:
            LOGGER.info("Resuming player `%s`", self.speaker_name)
            self.speaker.play()

        self._execute_with_recovery("resume", command)

    def stop(self) -> None:
        def command() -> None:
            LOGGER.info("Stopping player `%s` and clearing its queue", self.speaker_name)
            self.speaker.clear_queue()

        self._execute_with_recovery("stop", command)

    def handle_uri(self, uri):
        if self.sharelink.is_share_link(uri):
            return self.sharelink.add_share_link_to_queue(uri, position=1)
        return self.speaker.add_uri_to_queue(uri, position=1)


def _selected_group_from_runtime_group(
    group: ResolvedSonosGroupRuntime | None,
) -> SelectedSonosGroupSettings | None:
    if group is None:
        return None

    member_uids = [member.uid for member in group.members]
    for uid in group.missing_member_uids:
        if uid not in member_uids:
            member_uids.append(uid)

    return SelectedSonosGroupSettings(
        household_id=group.household_id,
        coordinator_uid=group.coordinator.uid,
        members=[SelectedSonosSpeakerSettings(uid=uid) for uid in member_uids],
    )
