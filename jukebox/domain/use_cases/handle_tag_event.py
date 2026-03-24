import logging

from jukebox.domain.entities import CurrentTagAction, PlaybackAction, PlaybackSession, TagEvent
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import CurrentTagRepository, LibraryRepository
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction

LOGGER = logging.getLogger("jukebox")


class HandleTagEvent:
    """Orchestrates the handling of a tag detection event."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        current_tag_repository: CurrentTagRepository,
        determine_action: DetermineAction,
        determine_current_tag_action: DetermineCurrentTagAction,
    ):
        self.player = player
        self.library = library
        self.current_tag_repository = current_tag_repository
        self.determine_action = determine_action
        self.determine_current_tag_action = determine_current_tag_action

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackSession:
        self._apply_current_tag_action_best_effort(tag_event, session)
        action = self.determine_action.execute(tag_event, session)

        LOGGER.debug(
            f"{action.value} \t\t {tag_event.tag_id} | {session.playing_tag} | "
            f"{session.paused_at} | {session.playing_tag_removed_at}"
        )

        if action == PlaybackAction.CONTINUE:
            # Reset when tag is present
            session.playing_tag_removed_at = None

        elif action == PlaybackAction.RESUME:
            self.player.resume()
            session.paused_at = None
            session.playing_tag_removed_at = None

        elif action == PlaybackAction.PLAY:
            LOGGER.info(f"Found card with UID: {tag_event.tag_id}")

            disc = self.library.get_disc(tag_event.tag_id) if tag_event.tag_id is not None else None
            if disc is not None:
                LOGGER.info(f"Found corresponding disc: {disc}")
                session.playing_tag = tag_event.tag_id
                self.player.play(disc.uri, disc.option.shuffle)
                session.paused_at = None
                session.playing_tag_removed_at = None
            else:
                LOGGER.warning(f"No disc found for UID: {tag_event.tag_id}")

        elif action == PlaybackAction.WAITING:
            # Grace period - tag removed but not pausing yet
            if session.playing_tag_removed_at is None:
                session.playing_tag_removed_at = tag_event.timestamp
            grace_period_elapsed = tag_event.timestamp - session.playing_tag_removed_at
            LOGGER.debug(f"Grace period: {grace_period_elapsed:.3f}s / {self.determine_action.pause_delay:g}s")

        elif action == PlaybackAction.PAUSE:
            self.player.pause()
            session.paused_at = tag_event.timestamp

        elif action == PlaybackAction.STOP:
            self.player.stop()
            session.playing_tag = None
            session.paused_at = None
            session.playing_tag_removed_at = None

        elif action == PlaybackAction.IDLE:
            pass

        else:
            LOGGER.warning(f"`{action.value}` action is not implemented yet")

        session.last_event_timestamp = tag_event.timestamp
        return session

    def _apply_current_tag_action_best_effort(self, tag_event: TagEvent, session: PlaybackSession) -> None:
        try:
            action = self.determine_current_tag_action.execute(tag_event, session)
            self._apply_current_tag_action(action, tag_event, session)
        except Exception as err:
            LOGGER.warning(
                f"Failed to sync current tag state; continuing tag handling: tag_id={tag_event.tag_id!r}, error={err}"
            )

    def _apply_current_tag_action(
        self, action: CurrentTagAction, tag_event: TagEvent, session: PlaybackSession
    ) -> None:
        if action == CurrentTagAction.SET:
            if tag_event.tag_id is None:
                LOGGER.error(
                    "`SET` action without tag_id",
                    extra={"event": tag_event, "session": session},
                )
                return
            self.current_tag_repository.set(tag_event.tag_id)
            session.physical_tag = tag_event.tag_id
            session.physical_tag_removed_at = None

        elif action == CurrentTagAction.CLEAR:
            self.current_tag_repository.clear()
            session.physical_tag = None
            session.physical_tag_removed_at = None

        elif action == CurrentTagAction.RESTORE:
            session.physical_tag_removed_at = None

        elif action == CurrentTagAction.REMOVE:
            session.physical_tag_removed_at = tag_event.timestamp

        elif action == CurrentTagAction.KEEP:
            pass  # No state changed
