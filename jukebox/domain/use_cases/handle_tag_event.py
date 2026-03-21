import logging

from jukebox.domain.entities import PlaybackAction, PlaybackSession, TagEvent
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import CurrentTagRepository, LibraryRepository
from jukebox.domain.use_cases.determine_action import DetermineAction

LOGGER = logging.getLogger("jukebox")
CURRENT_TAG_ABSENCE_GRACE_SECONDS = 1.0


class HandleTagEvent:
    """Orchestrates the handling of a tag detection event."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        current_tag_repository: CurrentTagRepository,
        determine_action: DetermineAction,
        current_tag_absence_grace_seconds: float = CURRENT_TAG_ABSENCE_GRACE_SECONDS,
    ):
        self.player = player
        self.library = library
        self.current_tag_repository = current_tag_repository
        self.determine_action = determine_action
        self.current_tag_absence_grace_seconds = current_tag_absence_grace_seconds

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackSession:
        elapsed_seconds = self._get_elapsed_seconds(tag_event, session)
        self._advance_session_clock(tag_event, session, elapsed_seconds)
        self._sync_current_tag_best_effort(tag_event, session)
        action = self.determine_action.execute(tag_event, session)

        LOGGER.debug(
            f"{action.value} \t\t {tag_event.tag_id} | {session.previous_tag} | "
            f"{session.awaiting_seconds} | {session.tag_removed_seconds}"
        )

        if action == PlaybackAction.CONTINUE:
            # Reset when tag is present
            session.tag_removed_seconds = 0

        elif action == PlaybackAction.RESUME:
            self.player.resume()
            session.awaiting_seconds = 0
            session.tag_removed_seconds = 0
            session.is_paused = False

        elif action == PlaybackAction.PLAY:
            LOGGER.info(f"Found card with UID: {tag_event.tag_id}")

            disc = self.library.get_disc(tag_event.tag_id) if tag_event.tag_id is not None else None
            if disc is not None:
                LOGGER.info(f"Found corresponding disc: {disc}")
                session.previous_tag = tag_event.tag_id
                self.player.play(disc.uri, disc.option.shuffle)
                session.awaiting_seconds = 0
                session.tag_removed_seconds = 0
                session.is_paused = False
            else:
                LOGGER.warning(f"No disc found for UID: {tag_event.tag_id}")

        elif action == PlaybackAction.WAITING:
            # Grace period - tag removed but not pausing yet
            LOGGER.debug(f"Grace period: {session.tag_removed_seconds:.3f}s / {self.determine_action.pause_delay:g}s")

        elif action == PlaybackAction.PAUSE:
            self.player.pause()
            session.awaiting_seconds = 0.0
            session.tag_removed_seconds = 0
            session.is_paused = True

        elif action == PlaybackAction.STOP:
            self.player.stop()
            session.previous_tag = None
            session.awaiting_seconds = 0.0
            session.tag_removed_seconds = 0
            session.is_paused = False

        elif action != PlaybackAction.IDLE:
            LOGGER.info(f"`{action.value}` action is not implemented yet")

        session.last_event_timestamp = tag_event.timestamp
        return session

    def _advance_session_clock(self, tag_event: TagEvent, session: PlaybackSession, elapsed_seconds: float) -> None:
        if elapsed_seconds <= 0:
            return

        if tag_event.tag_id is not None:
            session.physical_tag_removed_seconds = 0.0
            return

        if session.physical_tag is not None:
            session.physical_tag_removed_seconds += elapsed_seconds

        if session.is_paused:
            session.awaiting_seconds += elapsed_seconds
            return

        if session.previous_tag is not None:
            session.tag_removed_seconds += elapsed_seconds

    def _get_elapsed_seconds(self, tag_event: TagEvent, session: PlaybackSession) -> float:
        if session.last_event_timestamp is None:
            return 0.0
        return max(0.0, tag_event.timestamp - session.last_event_timestamp)

    def _sync_current_tag_best_effort(self, tag_event: TagEvent, session: PlaybackSession) -> None:
        try:
            self._sync_current_tag(tag_event, session)
        except Exception as err:
            LOGGER.warning(
                f"Failed to sync current tag state; continuing tag handling: tag_id={tag_event.tag_id!r}, error={err}"
            )

    def _sync_current_tag(self, tag_event: TagEvent, session: PlaybackSession) -> None:
        if tag_event.tag_id is not None:
            if session.physical_tag == tag_event.tag_id:
                session.physical_tag_removed_seconds = 0.0
                return

            self.current_tag_repository.set(tag_event.tag_id)
            session.physical_tag = tag_event.tag_id
            session.physical_tag_removed_seconds = 0.0
            return

        if session.physical_tag is None:
            return

        if session.physical_tag_removed_seconds < self.current_tag_absence_grace_seconds:
            return

        self.current_tag_repository.clear()
        session.physical_tag = None
        session.physical_tag_removed_seconds = 0.0
