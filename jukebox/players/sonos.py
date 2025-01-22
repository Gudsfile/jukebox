import os
from typing import Union

from soco import SoCo
from soco.plugins.sharelink import ShareLinkPlugin

from .player import Player


class SonosPlayer(Player):
    def __init__(self, host: Union[str, None] = None, **kwargs):
        if host is None:
            host = os.environ.get("SONOS_HOST", None)
        if host is None:
            raise ValueError("Host must be provided, either as an argument or in the SONOS_HOST environment variable.")
        self.speaker = SoCo(host)
        self.sharelink = ShareLinkPlugin(self.speaker)

    def play(self, uri: str, shuffle: bool):
        self.sharelink.soco.clear_queue()
        _ = self.sharelink.add_share_link_to_queue(uri, position=1)
        if shuffle:
            self.sharelink.soco.play_mode = "SHUFFLE_NOREPEAT"
        else:
            self.sharelink.soco.play_mode = "NORMAL"
        self.sharelink.soco.play_from_queue(index=0, start=True)

    def pause(self):
        self.speaker.pause()

    def resume(self):
        self.speaker.play()

    def stop(self):
        self.speaker.clear_queue()
