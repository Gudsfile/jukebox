import logging
import time
from time import sleep

from jukebox.domain.entities import PlaybackSession, TagEvent
from jukebox.domain.ports import ReaderPort
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent
from jukebox.shared.timing import DEFAULT_LOOP_INTERVAL_SECONDS

LOGGER = logging.getLogger("jukebox")


class CLIController:
    """CLI controller orchestrating the main loop."""

    def __init__(
        self,
        reader: ReaderPort,
        handle_tag_event: HandleTagEvent,
        loop_interval_seconds: float = DEFAULT_LOOP_INTERVAL_SECONDS,
    ):
        self.reader = reader
        self.handle_tag_event = handle_tag_event
        self.loop_interval_seconds = loop_interval_seconds

    def run(self):
        """Run the main event loop."""
        session = PlaybackSession()

        while True:
            loop_started = time.monotonic()
            tag_id = self.reader.read()
            tag_event = TagEvent(tag_id=tag_id, timestamp=time.monotonic())
            session = self.handle_tag_event.execute(tag_event, session)
            remaining_sleep = self.loop_interval_seconds - (time.monotonic() - loop_started)
            if remaining_sleep > 0:
                sleep(remaining_sleep)
