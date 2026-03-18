import logging

from jukebox.domain.entities import CurrentDisc, PlaybackAction, PlaybackSession, TagEvent
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import CurrentDiscRepository, LibraryRepository
from jukebox.domain.use_cases.determine_action import DetermineAction

LOGGER = logging.getLogger("jukebox")
CURRENT_DISC_ABSENCE_GRACE_SECONDS = 1.0


class HandleTagEvent:
    """Orchestrates the handling of a tag detection event."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        current_disc_repository: CurrentDiscRepository,
        determine_action: DetermineAction,
        current_disc_absence_grace_seconds: float = CURRENT_DISC_ABSENCE_GRACE_SECONDS,
    ):
        self.player = player
        self.library = library
        self.current_disc_repository = current_disc_repository
        self.determine_action = determine_action
        self.current_disc_absence_grace_seconds = current_disc_absence_grace_seconds

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackSession:
        elapsed_seconds = self._get_elapsed_seconds(tag_event, session)
        self._advance_session_clock(tag_event, session, elapsed_seconds)
        disc = self.library.get_disc(tag_event.tag_id) if tag_event.tag_id is not None else None
        self._sync_current_disc_best_effort(tag_event, session, disc is not None)
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

            if disc is not None:
                LOGGER.info(f"Found corresponding disc: {disc}")
                session.previous_tag = tag_event.tag_id
                self.player.play(disc.uri, disc.option.shuffle)
                session.awaiting_seconds = 0
                session.tag_removed_seconds = 0
                session.current_tag = tag_event.tag_id
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
            session.current_tag = None
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

    def _sync_current_disc_best_effort(
        self, tag_event: TagEvent, session: PlaybackSession, known_in_library: bool
    ) -> None:
        try:
            self._sync_current_disc(tag_event, session, known_in_library)
        except Exception as err:
            LOGGER.warning(
                "Failed to sync current disc state; continuing tag handling: "
                f"tag_id={tag_event.tag_id!r}, error={err}"
            )

    def _sync_current_disc(self, tag_event: TagEvent, session: PlaybackSession, known_in_library: bool) -> None:
        if tag_event.tag_id is not None:
            if (
                session.physical_tag == tag_event.tag_id
                and session.physical_tag_known_in_library == known_in_library
            ):
                session.physical_tag_removed_seconds = 0.0
                return

            self.current_disc_repository.save(
                CurrentDisc(tag_id=tag_event.tag_id, known_in_library=known_in_library)
            )
            session.physical_tag = tag_event.tag_id
            session.physical_tag_known_in_library = known_in_library
            session.physical_tag_removed_seconds = 0.0
            return

        if session.physical_tag is None:
            return

        if session.physical_tag_removed_seconds < self.current_disc_absence_grace_seconds:
            return

        self.current_disc_repository.clear_if_matches(session.physical_tag)
        session.physical_tag = None
        session.physical_tag_known_in_library = None
        session.physical_tag_removed_seconds = 0.0
