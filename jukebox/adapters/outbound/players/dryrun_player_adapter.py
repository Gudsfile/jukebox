import logging

from jukebox.domain.ports import PlayerPort

LOGGER = logging.getLogger("jukebox")


class DryrunPlayerAdapter(PlayerPort):
    """Adapter for dryrun player implementing PlayerPort."""

    def play(self, uri: str, shuffle: bool = False) -> None:
        LOGGER.info(f"Dryrun: Playing `{uri}` with shuffle={shuffle}")

    def pause(self) -> None:
        LOGGER.info("Dryrun: Pausing")

    def resume(self) -> None:
        LOGGER.info("Dryrun: Resuming")

    def stop(self) -> None:
        LOGGER.info("Dryrun: Stopping")
