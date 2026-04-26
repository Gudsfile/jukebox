import logging
from typing import Optional

import soco
from requests.exceptions import RequestException
from soco import SoCo
from soco.exceptions import SoCoException, SoCoUPnPException
from soco.plugins.sharelink import ShareLinkPlugin
from urllib3.exceptions import HTTPError

from jukebox.domain.ports import PlayerPort
from jukebox.settings.entities import ResolvedSonosGroupRuntime
from jukebox.settings.errors import InvalidSettingsError

LOGGER = logging.getLogger("jukebox")


def catch_soco_upnp_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SoCoUPnPException as err:
            if "UPnP Error 804" in str(err.message):
                LOGGER.warning("%s with `%s` failed, probably a bad uri: %s", func.__name__, args, err.message)
            elif "UPnP Error 701" in str(err.message):
                LOGGER.warning(
                    "%s with `%s` failed, probably a not available transition: %s",
                    func.__name__,
                    args,
                    err.message,
                )
            else:
                LOGGER.exception("%s with `%s` failed: %s", func.__name__, args, str(err))
            return

    return wrapper


class SonosPlayerAdapter(PlayerPort):
    """Adapter for Sonos player implementing PlayerPort."""

    def __init__(
        self,
        host: Optional[str] = None,
        name: Optional[str] = None,
        group: Optional[ResolvedSonosGroupRuntime] = None,
    ):
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

            speaker_info = self.speaker.get_speaker_info()
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise InvalidSettingsError(f"Failed to initialize Sonos player: {err}") from err

        LOGGER.info(
            "Found `%s` with software version: %s",
            self.speaker.player_name,
            speaker_info.get("software_version", None),
        )
        self.sharelink = ShareLinkPlugin(self.speaker)

    @staticmethod
    def _discover(name: Optional[str] = None) -> SoCo:
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
    def _get_rollback_coordinator_for_join(speaker: SoCo) -> Optional[SoCo]:
        current_group = speaker.group
        if current_group is None:
            return None

        current_coordinator = current_group.coordinator
        if current_coordinator is None or current_coordinator.uid == speaker.uid:
            return None

        return current_coordinator

    @catch_soco_upnp_exception
    def play(self, uri: str, shuffle: bool = False) -> None:
        LOGGER.info("Playing `%s` on the player `%s`", uri, self.speaker.player_name)
        self.speaker.clear_queue()
        _ = self.handle_uri(uri)
        self.speaker.play_mode = "SHUFFLE_NOREPEAT" if shuffle else "NORMAL"
        self.speaker.play_from_queue(index=0, start=True)

    @catch_soco_upnp_exception
    def pause(self) -> None:
        LOGGER.info("Pausing player `%s`", self.speaker.player_name)
        self.speaker.pause()

    @catch_soco_upnp_exception
    def resume(self) -> None:
        LOGGER.info("Resuming player `%s`", self.speaker.player_name)
        self.speaker.play()

    @catch_soco_upnp_exception
    def stop(self) -> None:
        LOGGER.info("Stopping player `%s` and clearing its queue", self.speaker.player_name)
        self.speaker.clear_queue()

    def handle_uri(self, uri):
        if self.sharelink.is_share_link(uri):
            return self.sharelink.add_share_link_to_queue(uri, position=1)
        return self.speaker.add_uri_to_queue(uri, position=1)
