import logging
from collections.abc import Callable

from jukebox.domain.entities import CurrentTagAction, PlaybackAction, PlaybackCommandRetry, PlaybackSession, TagEvent
from jukebox.domain.errors import PlaybackError
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import CurrentTagRepository, LibraryRepository
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction

LOGGER = logging.getLogger("jukebox")
PLAYBACK_RETRY_DELAYS_SECONDS = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)


class HandleTagEvent:
    """Orchestrates the handling of a tag detection event."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        current_tag_repository: CurrentTagRepository,
        determine_action: DetermineAction,
        determine_current_tag_action: DetermineCurrentTagAction,
        retry_delays_seconds: tuple[float, ...] = PLAYBACK_RETRY_DELAYS_SECONDS,
    ):
        self.player = player
        self.library = library
        self.current_tag_repository = current_tag_repository
        self.determine_action = determine_action
        self.determine_current_tag_action = determine_current_tag_action
        if not retry_delays_seconds:
            raise ValueError("retry_delays_seconds must not be empty")
        self.retry_delays_seconds = retry_delays_seconds

    def execute(self, tag_event: TagEvent, session: PlaybackSession) -> PlaybackSession:
        self._apply_current_tag_action_best_effort(tag_event, session)
        action = self.determine_action.execute(tag_event, session)

        LOGGER.debug(
            "%s \t\t %s | %s | %s | %s",
            action.value,
            tag_event.tag_id,
            session.playing_tag,
            session.paused_at,
            session.playing_tag_removed_at,
        )

        match action:
            case PlaybackAction.CONTINUE:
                # Reset when tag is present
                session.playing_tag_removed_at = None
                if (
                    session.playback_command_retry is not None
                    and session.playback_command_retry.action == PlaybackAction.PAUSE
                ):
                    session.playback_command_retry = None

            case PlaybackAction.RESUME:
                if self._run_playback_command(
                    action=PlaybackAction.RESUME,
                    timestamp=tag_event.timestamp,
                    session=session,
                    error_message="Playback operation `RESUME` failed; stopping session update",
                    command=self.player.resume,
                ):
                    session.paused_at = None
                    session.playing_tag_removed_at = None

            case PlaybackAction.PLAY:
                LOGGER.info("Found card with UID: %s", tag_event.tag_id)

                disc = self.library.get_disc(tag_event.tag_id) if tag_event.tag_id is not None else None
                if disc is not None:
                    LOGGER.info("Found corresponding disc: %s", disc)
                    if self._run_playback_command(
                        action=PlaybackAction.PLAY,
                        tag_id=tag_event.tag_id,
                        timestamp=tag_event.timestamp,
                        session=session,
                        error_message=(
                            f"Playback operation `PLAY` failed for tag_id='{tag_event.tag_id}'; stopping session update"
                        ),
                        command=lambda: self.player.play(disc.uri, disc.option.shuffle),
                    ):
                        session.playing_tag = tag_event.tag_id
                        session.paused_at = None
                        session.playing_tag_removed_at = None
                else:
                    session.playback_command_retry = None
                    LOGGER.warning("No disc found for UID: %s", tag_event.tag_id)

            case PlaybackAction.WAITING:
                # Grace period - tag removed but not pausing yet
                if session.playing_tag_removed_at is None:
                    session.playing_tag_removed_at = tag_event.timestamp
                grace_period_elapsed = tag_event.timestamp - session.playing_tag_removed_at
                LOGGER.debug("Grace period: %.3fs / %gs", grace_period_elapsed, self.determine_action.pause_delay)

            case PlaybackAction.PAUSE:
                if self._run_playback_command(
                    action=PlaybackAction.PAUSE,
                    timestamp=tag_event.timestamp,
                    session=session,
                    error_message="Playback operation `PAUSE` failed; stopping session update",
                    command=self.player.pause,
                ):
                    session.paused_at = tag_event.timestamp

            case PlaybackAction.STOP:
                if self._run_playback_command(
                    action=PlaybackAction.STOP,
                    timestamp=tag_event.timestamp,
                    session=session,
                    error_message="Playback operation `STOP` failed; stopping session update",
                    command=self.player.stop,
                ):
                    session.playing_tag = None
                    session.paused_at = None
                    session.playing_tag_removed_at = None

            case PlaybackAction.IDLE:
                pass

            case _:
                LOGGER.warning("`%s` action is not implemented yet", action.value)

        session.last_event_timestamp = tag_event.timestamp
        return session

    def _apply_current_tag_action_best_effort(self, tag_event: TagEvent, session: PlaybackSession) -> None:
        try:
            action = self.determine_current_tag_action.execute(tag_event, session)
            self._apply_current_tag_action(action, tag_event, session)
        except Exception as err:
            LOGGER.warning(
                "Failed to sync current tag state; continuing tag handling: tag_id=%r, error=%s",
                tag_event.tag_id,
                err,
            )

    def _apply_current_tag_action(
        self, action: CurrentTagAction, tag_event: TagEvent, session: PlaybackSession
    ) -> None:
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
                pass  # No state changed

    def _run_playback_command(
        self,
        *,
        action: PlaybackAction,
        timestamp: float,
        session: PlaybackSession,
        error_message: str,
        command: Callable[[], None],
        tag_id: str | None = None,
    ) -> bool:
        retry = session.playback_command_retry
        retry_matches = retry is not None and retry.matches(action=action, tag_id=tag_id)
        if retry_matches and retry.exhausted:
            LOGGER.debug(
                "Skipping playback operation `%s`; retry exhausted after %d attempts",
                action.value.upper(),
                retry.attempt_count,
            )
            return False

        if retry_matches and retry.next_retry_at is not None and timestamp < retry.next_retry_at:
            LOGGER.debug(
                "Skipping playback operation `%s` until retry time %.3f",
                action.value.upper(),
                retry.next_retry_at,
            )
            return False

        try:
            command()
        except PlaybackError:
            retry = self._record_playback_command_failure(
                action=action,
                timestamp=timestamp,
                session=session,
                tag_id=tag_id,
            )
            if retry.exhausted:
                LOGGER.warning("%s; retry exhausted after %d attempts", error_message, retry.attempt_count)
            else:
                next_retry_at = retry.next_retry_at
                if next_retry_at is None:
                    raise RuntimeError("retry is not exhausted but next_retry_at is missing")
                LOGGER.warning("%s; retrying in %.3fs", error_message, next_retry_at - timestamp)
            return False

        session.playback_command_retry = None
        return True

    def _record_playback_command_failure(
        self,
        *,
        action: PlaybackAction,
        timestamp: float,
        session: PlaybackSession,
        tag_id: str | None = None,
    ) -> PlaybackCommandRetry:
        existing_retry = session.playback_command_retry
        if existing_retry is None or not existing_retry.matches(action=action, tag_id=tag_id):
            attempt_count = 1
            first_failed_at = timestamp
        else:
            attempt_count = existing_retry.attempt_count + 1
            first_failed_at = existing_retry.first_failed_at

        retry_delay = self._retry_delay_for_attempt(attempt_count)
        retry = PlaybackCommandRetry(
            action=action,
            tag_id=tag_id,
            first_failed_at=first_failed_at,
            last_failed_at=timestamp,
            attempt_count=attempt_count,
            next_retry_at=None if retry_delay is None else timestamp + retry_delay,
            exhausted=retry_delay is None,
        )
        session.playback_command_retry = retry
        return retry

    def _retry_delay_for_attempt(self, attempt_count: int) -> float | None:
        delay_index = attempt_count - 1
        if delay_index >= len(self.retry_delays_seconds):
            return None
        return self.retry_delays_seconds[delay_index]
