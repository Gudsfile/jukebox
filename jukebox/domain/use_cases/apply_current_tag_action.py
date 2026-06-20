import logging

from jukebox.domain.entities import CurrentTagAction, CurrentTagSession, TagEvent
from jukebox.domain.repositories import CurrentTagRepository

LOGGER = logging.getLogger("jukebox")


class ApplyCurrentTagAction:
    """Applies a CurrentTagAction to the repository and session state."""

    def __init__(self, current_tag_repository: CurrentTagRepository):
        self.current_tag_repository = current_tag_repository

    def execute(self, action: CurrentTagAction, tag_event: TagEvent, session: CurrentTagSession) -> None:
        match action:
            case CurrentTagAction.SET:
                if tag_event.tag_id is None:
                    LOGGER.error(
                        "`SET` action without tag_id",
                        extra={"event": tag_event, "session": session},
                    )
                    return
                self.current_tag_repository.set(tag_event.tag_id)
                session.physical_tag = tag_event.tag_id
                session.physical_tag_removed_at = None

            case CurrentTagAction.CLEAR:
                self.current_tag_repository.clear()
                session.physical_tag = None
                session.physical_tag_removed_at = None

            case CurrentTagAction.RESTORE:
                session.physical_tag_removed_at = None

            case CurrentTagAction.REMOVE:
                session.physical_tag_removed_at = tag_event.timestamp

            case CurrentTagAction.KEEP:
                pass
