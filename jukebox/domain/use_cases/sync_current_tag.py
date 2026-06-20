import dataclasses
import logging

from jukebox.domain.entities import CurrentTagContext, CurrentTagState, TagEvent
from jukebox.domain.repositories import CurrentTagRepository
from jukebox.domain.use_cases.transition_current_tag import transition_current_tag

LOGGER = logging.getLogger("jukebox")


class SyncCurrentTag:
    """Best-effort sync of physical current tag state with the repository."""

    def __init__(self, repository: CurrentTagRepository, ctx: CurrentTagContext):
        self.repository = repository
        self.ctx = ctx

    def execute(self, tag_event: TagEvent, state: CurrentTagState) -> CurrentTagState:
        try:
            (success_state, command) = transition_current_tag(state, tag_event, self.ctx)
            if command == "set":
                assert tag_event.tag_id is not None
                self.repository.set(tag_event.tag_id)
            elif command == "clear":
                self.repository.clear()
            next_state = success_state
        except Exception as err:
            LOGGER.warning(
                "Failed to sync current tag state; continuing, tag state may be stale: tag_id=%r, error=%s",
                tag_event.tag_id,
                err,
            )
            next_state = state
        return dataclasses.replace(next_state, last_event_timestamp=tag_event.timestamp)
