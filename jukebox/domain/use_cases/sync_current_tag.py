import logging

from jukebox.domain.entities import PlaybackSession, TagEvent
from jukebox.domain.use_cases.apply_current_tag_action import ApplyCurrentTagAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction

LOGGER = logging.getLogger("jukebox")


class SyncCurrentTag:
    """Best-effort sync of physical current tag state with repository and session."""

    def __init__(
        self,
        determine_current_tag_action: DetermineCurrentTagAction,
        apply_current_tag_action: ApplyCurrentTagAction,
    ):
        self.determine_current_tag_action = determine_current_tag_action
        self.apply_current_tag_action = apply_current_tag_action

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> None:
        try:
            action = self.determine_current_tag_action.execute(tag_event, session)
            self.apply_current_tag_action.execute(action, tag_event, session)
        except Exception as err:
            LOGGER.warning(
                "Failed to sync current tag state; continuing, tag state may be stale: tag_id=%r, error=%s",
                tag_event.tag_id,
                err,
            )
        finally:
            current_tag_session.last_event_timestamp = tag_event.timestamp
