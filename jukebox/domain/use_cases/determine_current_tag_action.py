from jukebox.domain.entities import CurrentTagAction, PlaybackSession, TagEvent

CURRENT_TAG_ABSENCE_GRACE_SECONDS = 1.0


class DetermineCurrentTagAction:
    """Determines what action to take on the physical current tag state."""

    def __init__(self, grace_seconds: float = CURRENT_TAG_ABSENCE_GRACE_SECONDS):
        self.grace_seconds = grace_seconds

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> CurrentTagAction:
        if tag_event.tag_id is not None:
            if session.physical_tag == tag_event.tag_id:
                return CurrentTagAction.KEEP
            return CurrentTagAction.SET

        if session.physical_tag is None:
            return CurrentTagAction.KEEP

        if session.physical_tag_removed_seconds < self.grace_seconds:
            return CurrentTagAction.KEEP

        return CurrentTagAction.CLEAR
