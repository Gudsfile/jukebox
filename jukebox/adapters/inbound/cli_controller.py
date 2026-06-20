import time
from time import sleep

from jukebox.domain.entities import CurrentTagSession, Idle, PlaybackState, TagEvent
from jukebox.domain.ports import ReaderPort
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent
from jukebox.domain.use_cases.sync_current_tag import SyncCurrentTag
from jukebox.shared.timing import DEFAULT_LOOP_INTERVAL_SECONDS


class CLIController:
    """CLI controller orchestrating the main loop."""

    def __init__(
        self,
        reader: ReaderPort,
        handle_tag_event: HandleTagEvent,
        sync_current_tag: SyncCurrentTag,
        loop_interval_seconds: float = DEFAULT_LOOP_INTERVAL_SECONDS,
    ):
        self.reader = reader
        self.handle_tag_event = handle_tag_event
        self.sync_current_tag = sync_current_tag
        self.loop_interval_seconds = loop_interval_seconds

    def run(self):
        """Run the main event loop."""
        state: PlaybackState = Idle()
        current_tag_session = CurrentTagSession()

        while True:
            loop_started = time.monotonic()
            tag_id = self.reader.read()
            tag_event = TagEvent(tag_id=tag_id, timestamp=time.monotonic())
            self.sync_current_tag.execute(tag_event, current_tag_session)
            state = self.handle_tag_event.execute(tag_event, state)
            remaining_sleep = self.loop_interval_seconds - (time.monotonic() - loop_started)
            if remaining_sleep > 0:
                sleep(remaining_sleep)
