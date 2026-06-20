from jukebox.domain.entities import (
    Disc,
    Idle,
    Paused,
    PlaybackCommand,
    PlaybackState,
    Playing,
    TagEvent,
    TransitionContext,
    Waiting,
)


def _play_or_stay(
    tag_id: str, disc: Disc | None, fallback: PlaybackState
) -> tuple[PlaybackState, PlaybackCommand | None]:
    """Play the new disc if available, otherwise clear retry and stay in current state."""
    if disc is not None:
        return Playing(tag=tag_id), "play"
    return fallback, None


def transition_playback(
    state: PlaybackState,
    tag_event: TagEvent,
    disc: Disc | None,
    ctx: TransitionContext,
) -> tuple[PlaybackState, PlaybackCommand | None]:
    """
    Playback state transition.

    Returns (success_state, command) where command is one of
    "play" | "pause" | "resume" | "stop" | None.

    When command is None the transition is immediate (no player I/O).
    When command is not None, the caller executes the command and adopts
    success_state only on success; on failure it retries from the current state.
    """
    tag_id = tag_event.tag_id
    timestamp = tag_event.timestamp

    match state:
        case Idle():
            if tag_id is not None:
                return _play_or_stay(tag_id, disc, Idle())
            return state, None  # no tag, preserve retry for next read

        case Playing(tag=playing_tag):
            if tag_id is None:
                return Waiting(tag=playing_tag, removed_at=timestamp), None
            if tag_id == playing_tag:
                return Playing(tag=playing_tag), None
            return _play_or_stay(tag_id, disc, Playing(tag=playing_tag))

        case Waiting(tag=playing_tag, removed_at=removed_at):
            if tag_id is not None:
                if tag_id == playing_tag:
                    return Playing(tag=playing_tag), None
                return _play_or_stay(tag_id, disc, Waiting(tag=playing_tag, removed_at=removed_at))
            removal_duration = timestamp - removed_at
            if removal_duration < ctx.pause_delay:
                return state, None
            return Paused(tag=playing_tag, paused_at=timestamp), "pause"

        case Paused(tag=playing_tag, paused_at=paused_at):
            paused_duration = timestamp - paused_at
            is_acceptable_pause = paused_duration < ctx.max_pause_duration
            if tag_id is not None:
                if tag_id == playing_tag and is_acceptable_pause:
                    return Playing(tag=playing_tag), "resume"
                return _play_or_stay(tag_id, disc, Paused(tag=playing_tag, paused_at=paused_at))
            if is_acceptable_pause:
                return state, None
            return Idle(), "stop"
