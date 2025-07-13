import logging

from .player import Player

LOGGER = logging.getLogger("jukebox")


class DryRunPlayer(Player):
    def __init__(self, **kwargs):
        LOGGER.info("Creating player")

    def play(self, uri: str, shuffle: bool):
        LOGGER.info(f"Random playback of `{uri}` on the player" if shuffle else f"Playing `{uri}` on player")

    def pause(self):
        LOGGER.info("Pausing player")

    def resume(self):
        LOGGER.info("Resuming player")

    def stop(self):
        LOGGER.info("Stopping player")
