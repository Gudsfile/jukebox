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
                LOGGER.warning(f"{func.__name__} with `{args}` failed, probably a bad uri: {str(err.message)}")
            elif "UPnP Error 701" in str(err.message):
                LOGGER.warning(
                    f"{func.__name__} with `{args}` failed, probably a not available transition: {str(err.message)}"
                )
            else:
                LOGGER.error(f"{func.__name__} with `{args}` failed", err)
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
                self._enforce_group(group)
            elif host:
                self.speaker = SoCo(host)
            else:
                self.speaker = self._discover(name)

            speaker_info = self.speaker.get_speaker_info()
        except (HTTPError, OSError, RequestException, RuntimeError, SoCoException, SoCoUPnPException) as err:
            raise InvalidSettingsError(f"Failed to initialize Sonos player: {err}") from err

        LOGGER.info(
            f"Found `{self.speaker.player_name}` with software version: {speaker_info.get('software_version', None)}"
        )
        self.sharelink = ShareLinkPlugin(self.speaker)

    @staticmethod
    def _discover(name: Optional[str] = None) -> SoCo:
        discovered = soco.discover()
        if not discovered:
            raise RuntimeError("No Sonos speakers found on the network")
        speakers = sorted(discovered, key=lambda s: s.player_name)
        LOGGER.info(f"Discovered {len(speakers)} Sonos speaker(s): {[s.player_name for s in speakers]}")
        if name:
            matching = [s for s in speakers if s.player_name == name]
            if len(matching) > 1:
                LOGGER.warning(
                    f"Multiple Sonos speakers with name '{name}' found. Using first match. "
                    "Consider using host IP to disambiguate."
                )
            if matching:
                return matching[0]
            raise RuntimeError(f"No Sonos speaker named '{name}' found on the network")
        return speakers[0]

    def _enforce_group(self, group: ResolvedSonosGroupRuntime) -> None:
        desired_member_uids = {member.uid for member in group.members}
        speakers_by_uid = {member.uid: SoCo(member.host) for member in group.members}
        coordinator = speakers_by_uid[group.coordinator.uid]

        current_group = coordinator.group
        if current_group is not None:
            for current_member in list(current_group.members):
                if current_member.uid in desired_member_uids:
                    continue

                LOGGER.info(
                    f"Removing Sonos speaker `{current_member.player_name}` from coordinator group before playback"
                )
                current_member.unjoin()

        for member in group.members:
            if member.uid == group.coordinator.uid:
                continue

            speaker = speakers_by_uid[member.uid]
            if self._is_joined_to_coordinator(speaker, coordinator):
                continue

            LOGGER.info(f"Joining Sonos speaker `{speaker.player_name}` to `{coordinator.player_name}` before playback")
            speaker.join(coordinator)

    @staticmethod
    def _is_joined_to_coordinator(speaker: SoCo, coordinator: SoCo) -> bool:
        current_group = speaker.group
        if current_group is None:
            return False

        current_coordinator = current_group.coordinator
        if current_coordinator is None:
            return False

        return current_coordinator.uid == coordinator.uid

    @catch_soco_upnp_exception
    def play(self, uri: str, shuffle: bool = False) -> None:
        LOGGER.info(f"Playing `{uri}` on the player `{self.speaker.player_name}`")
        self.speaker.clear_queue()
        _ = self.handle_uri(uri)
        self.speaker.play_mode = "SHUFFLE_NOREPEAT" if shuffle else "NORMAL"
        self.speaker.play_from_queue(index=0, start=True)

    @catch_soco_upnp_exception
    def pause(self) -> None:
        LOGGER.info(f"Pausing player `{self.speaker.player_name}`")
        self.speaker.pause()

    @catch_soco_upnp_exception
    def resume(self) -> None:
        LOGGER.info(f"Resuming player `{self.speaker.player_name}`")
        self.speaker.play()

    @catch_soco_upnp_exception
    def stop(self) -> None:
        LOGGER.info(f"Stopping player `{self.speaker.player_name}` and clearing its queue")
        self.speaker.clear_queue()

    def handle_uri(self, uri):
        if self.sharelink.is_share_link(uri):
            return self.sharelink.add_share_link_to_queue(uri, position=1)
        return self.speaker.add_uri_to_queue(uri, position=1)
