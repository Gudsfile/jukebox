import logging

from jukebox.domain.entities import PlaybackAction, PlaybackSession, TagEvent
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import LibraryRepository
from jukebox.domain.use_cases.determine_action import DetermineAction

LOGGER = logging.getLogger("jukebox")


class HandleTagEvent:
    """Orchestrates the handling of a tag detection event."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        determine_action: DetermineAction,
    ):
        self.player = player
        self.library = library
        self.determine_action = determine_action

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackSession:
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

        elif action == PlaybackAction.PLAY:
            LOGGER.info(f"Found card with UID: {tag_event.tag_id}")

            disc = self.library.get_disc(tag_event.tag_id) if tag_event.tag_id else None
            if disc is not None:
                LOGGER.info(f"Found corresponding disc: {disc}")
                session.previous_tag = tag_event.tag_id
                self.player.play(disc.uri, disc.option.shuffle)
                session.awaiting_seconds = 0
                session.tag_removed_seconds = 0
                session.current_tag = tag_event.tag_id
            else:
                LOGGER.warning(f"No disc found for UID: {tag_event.tag_id}")

        elif action == PlaybackAction.WAITING:
            # Grace period - tag removed but not pausing yet
            session.tag_removed_seconds += 0.5
            LOGGER.debug(f"Grace period: {session.tag_removed_seconds:.1f}s / {self.determine_action.pause_delay}s")

        elif action == PlaybackAction.PAUSE:
            self.player.pause()
            session.awaiting_seconds += 0.5
            session.tag_removed_seconds = 0
            session.is_paused = True

        elif action == PlaybackAction.STOP:
            self.player.stop()
            session.previous_tag = None
            session.current_tag = None
            session.tag_removed_seconds = 0
            session.is_paused = False

        elif action == PlaybackAction.IDLE:
            if session.awaiting_seconds < self.determine_action.max_pause_duration:
                session.awaiting_seconds += 0.5
        else:
            LOGGER.info(f"`{action.value}` action is not implemented yet")

        return session
