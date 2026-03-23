from jukebox.domain.entities import PlaybackAction, PlaybackSession, TagEvent


class DetermineAction:
    """Determines what action to take based on tag event and current session state."""

    def __init__(self, pause_delay: float, max_pause_duration: int):
        self.pause_delay = pause_delay
        self.max_pause_duration = max_pause_duration

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackAction:
        current_tag = tag_event.tag_id
        playing_tag = session.playing_tag
        pause_duration_seconds = session.pause_duration_seconds
        tag_removed_at = session.playing_tag_removed_at

        removal_duration = tag_event.timestamp - tag_removed_at if tag_removed_at is not None else 0.0

        is_detecting_tag = current_tag is not None
        is_same_tag_as_previous = current_tag == playing_tag
        is_paused = session.is_paused
        is_acceptable_pause_duration = pause_duration_seconds < self.max_pause_duration
        is_within_grace_period = removal_duration < self.pause_delay

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
