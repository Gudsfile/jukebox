import logging
import os
from typing import Union

from soco import SoCo
from soco.plugins.sharelink import ShareLinkPlugin

from .player import Player

LOGGER = logging.getLogger("jukebox")


class SonosPlayer(Player):
    def __init__(self, host: Union[str, None] = None, **kwargs):
        if host is None:
            host = os.environ.get("SONOS_HOST", None)
        if host is None:
            raise ValueError("Host must be provided, either as an argument or in the SONOS_HOST environment variable.")
        self.speaker = SoCo(host)
        LOGGER.info(
            f"Found `{self.speaker.player_name}` with software version: {self.speaker.get_speaker_info().get('software_version', None)}"
        )
        self.sharelink = ShareLinkPlugin(self.speaker)

    def play(self, uri: str, shuffle: bool):
        LOGGER.info(f"Playing `{uri}` on the player `{self.speaker.player_name}`")
        self.sharelink.soco.clear_queue()
        _ = self.sharelink.add_share_link_to_queue(uri, position=1)
        if shuffle:
            self.sharelink.soco.play_mode = "SHUFFLE_NOREPEAT"
        else:
            self.sharelink.soco.play_mode = "NORMAL"
        self.sharelink.soco.play_from_queue(index=0, start=True)

    def pause(self):
        LOGGER.info(f"Pausing player `{self.speaker.player_name}`")
        self.speaker.pause()

    def resume(self):
        LOGGER.info(f"Resuming player `{self.speaker.player_name}`")
        self.speaker.play()

    def stop(self):
        LOGGER.info(f"Stopping player `{self.speaker.player_name}` and clearing its queue")
        self.speaker.clear_queue()
