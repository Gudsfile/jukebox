import logging

from jukebox.domain.entities import PlaybackAction, PlaybackSession, TagEvent

LOGGER = logging.getLogger("jukebox")


class DetermineAction:
    """Determines what action to take based on tag event and current session state."""

    def __init__(self, pause_delay: int, max_pause_duration: int):
        self.pause_delay = pause_delay
        self.max_pause_duration = max_pause_duration

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackAction:
        current_tag = tag_event.tag_id
        previous_tag = session.previous_tag
        awaiting_seconds = session.awaiting_seconds
        tag_removed_seconds = session.tag_removed_seconds

        is_detecting_tag = current_tag is not None
        is_same_tag_as_previous = current_tag == previous_tag
        is_paused = awaiting_seconds > 0
        is_acceptable_pause_duration = awaiting_seconds < self.max_pause_duration
        is_within_grace_period = tag_removed_seconds < self.pause_delay

        if is_detecting_tag and is_same_tag_as_previous and not is_paused:
            return PlaybackAction.CONTINUE
        elif is_detecting_tag and is_same_tag_as_previous and is_paused and is_acceptable_pause_duration:
            return PlaybackAction.RESUME
        elif is_detecting_tag:
            return PlaybackAction.PLAY
        elif not is_detecting_tag and not is_same_tag_as_previous and not is_paused and is_within_grace_period:
            return PlaybackAction.WAITING
        elif not is_detecting_tag and not is_same_tag_as_previous and not is_paused and is_acceptable_pause_duration:
            return PlaybackAction.PAUSE
        elif not is_detecting_tag and not is_same_tag_as_previous and not is_acceptable_pause_duration:
            return PlaybackAction.STOP
        return PlaybackAction.IDLE
