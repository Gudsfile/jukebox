import dataclasses
import logging

from jukebox.domain.entities import (
    Disc,
    PlaybackCommand,
    PlaybackState,
    Playing,
    RetryState,
    TagEvent,
    TransitionContext,
    Waiting,
)
from jukebox.domain.errors import PlaybackError
from jukebox.domain.ports import PlayerPort
from jukebox.domain.repositories import LibraryRepository
from jukebox.domain.use_cases.transition_playback import transition

LOGGER = logging.getLogger("jukebox")


class HandleTagEvent:
    """Executes playback commands determined by the state transition function."""

    def __init__(
        self,
        player: PlayerPort,
        library: LibraryRepository,
        ctx: TransitionContext,
    ):
        self.player = player
        self.library = library
        self.ctx = ctx

    def execute(self, tag_event: TagEvent, state: PlaybackState) -> PlaybackState:
        tag_id = tag_event.tag_id
        disc: Disc | None = None
        if tag_id is not None and not (isinstance(state, (Playing, Waiting)) and state.tag == tag_id):
            disc = self.library.get_disc(tag_id)

        (success_state, command) = transition(state, tag_event, disc, self.ctx)

        LOGGER.debug("%s  %s | %s", (command or "none").upper(), tag_id, type(state).__name__)

        if command is None:
            return success_state

        if command == "play":
            LOGGER.info("Found card with UID: %s", tag_id)
            LOGGER.info("Found corresponding disc: %s", disc)

        return self._try_execute(state, success_state, command, tag_event, disc)

    def _try_execute(
        self,
        current_state: PlaybackState,
        success_state: PlaybackState,
        command: PlaybackCommand,
        tag_event: TagEvent,
        disc: Disc | None,
    ) -> PlaybackState:
        tag_id = tag_event.tag_id if command == "play" else None
        timestamp = tag_event.timestamp
        retry = current_state.retry
        retry_matches = retry is not None and retry.matches(action=command, tag_id=tag_id)

        if retry_matches and retry.exhausted:
            LOGGER.debug(
                "Skipping %s; retry exhausted after %d attempts",
                command.upper(),
                retry.attempt_count,
            )
            return current_state

        if retry_matches and retry.next_retry_at is not None and timestamp < retry.next_retry_at:
            LOGGER.debug("Skipping %s until retry time %.3f", command.upper(), retry.next_retry_at)
            return current_state

        try:
            match command:
                case "play":
                    assert disc is not None
                    self.player.play(disc.uri, disc.option.shuffle)
                case "pause":
                    self.player.pause()
                case "resume":
                    self.player.resume()
                case "stop":
                    self.player.stop()
        except PlaybackError:
            new_retry = self._build_retry(
                existing=retry if retry_matches else None,
                action=command,
                tag_id=tag_id,
                timestamp=timestamp,
            )
            if new_retry.exhausted:
                LOGGER.warning(
                    "Playback %s failed; retry exhausted after %d attempts", command, new_retry.attempt_count
                )
            else:
                LOGGER.warning(
                    "Playback %s failed; retrying in %.3fs", command, (new_retry.next_retry_at or 0) - timestamp
                )
            return dataclasses.replace(current_state, retry=new_retry)

        return success_state

    def _build_retry(
        self,
        *,
        existing: RetryState | None,
        action: PlaybackCommand,
        tag_id: str | None,
        timestamp: float,
    ) -> RetryState:
        if existing is None:
            attempt_count = 1
            first_failed_at = timestamp
        else:
            attempt_count = existing.attempt_count + 1
            first_failed_at = existing.first_failed_at

        retry_delay = self._retry_delay_for_attempt(attempt_count)
        return RetryState(
            action=action,
            tag_id=tag_id,
            first_failed_at=first_failed_at,
            last_failed_at=timestamp,
            attempt_count=attempt_count,
            next_retry_at=None if retry_delay is None else timestamp + retry_delay,
            exhausted=retry_delay is None,
        )

    def _retry_delay_for_attempt(self, attempt_count: int) -> float | None:
        delay_index = attempt_count - 1
        if delay_index >= len(self.ctx.retry_delays):
            return None
        return self.ctx.retry_delays[delay_index]
