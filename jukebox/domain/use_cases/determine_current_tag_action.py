from jukebox.domain.entities import CurrentTagAction, PlaybackSession, TagEvent

CURRENT_TAG_ABSENCE_GRACE_SECONDS = 1.0


class DetermineCurrentTagAction:
    """Determines what action to take on the physical current tag state."""

    def __init__(self, grace_seconds: float = CURRENT_TAG_ABSENCE_GRACE_SECONDS):
        self.grace_seconds = grace_seconds

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> CurrentTagAction:
        if tag_event.tag_id is not None:
            if session.physical_tag == tag_event.tag_id:
                if session.physical_tag_removed_at is None:
                    return CurrentTagAction.KEEP
                return CurrentTagAction.RESTORE
            return CurrentTagAction.SET

        if session.physical_tag is None:
            return CurrentTagAction.KEEP

        if session.physical_tag_removed_at is not None:
            removal_duration = tag_event.timestamp - session.physical_tag_removed_at
            if removal_duration < self.grace_seconds:
                return CurrentTagAction.KEEP
            return CurrentTagAction.CLEAR

        if session.last_event_timestamp is not None:
            elapsed_since_last_event = tag_event.timestamp - session.last_event_timestamp
            if elapsed_since_last_event < self.grace_seconds:
                return CurrentTagAction.REMOVE
            return CurrentTagAction.CLEAR

        return CurrentTagAction.KEEP
