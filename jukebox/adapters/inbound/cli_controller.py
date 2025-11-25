import logging
import time
from time import sleep

from jukebox.domain.entities import PlaybackSession, TagEvent
from jukebox.domain.ports import ReaderPort
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent

LOGGER = logging.getLogger("jukebox")


class CLIController:
    """CLI controller orchestrating the main loop."""

    def __init__(
        self,
        reader: ReaderPort,
        handle_tag_event: HandleTagEvent,
    ):
        self.reader = reader
        self.handle_tag_event = handle_tag_event

    def run(self):
        """Run the main event loop."""
        session = PlaybackSession()

        while True:
            tag_id = self.reader.read()
            tag_event = TagEvent(tag_id=tag_id, timestamp=time.time())
            session = self.handle_tag_event.execute(tag_event, session)
            sleep(0.5)
