from jukebox.domain.entities import (
    CurrentTagCommand,
    CurrentTagContext,
    CurrentTagState,
    NoTag,
    TagEvent,
    TagPresent,
    TagRemoved,
)


def transition_current_tag(
    state: CurrentTagState,
    tag_event: TagEvent,
    ctx: CurrentTagContext,
) -> tuple[CurrentTagState, CurrentTagCommand | None]:
    """
    Current-tag state transition.

    Returns (next_state, command) where command is "set" | "clear" | None.
    When command is None the transition is immediate (no repository I/O).
    The caller stamps last_event_timestamp unconditionally after calling this.
    """
    tag_id = tag_event.tag_id
    timestamp = tag_event.timestamp

    match state:
        case NoTag():
            if tag_id is not None:
                return TagPresent(tag=tag_id), "set"
            return state, None

        case TagPresent(tag=present_tag):
            if tag_id is not None:
                if tag_id == present_tag:
                    return TagPresent(tag=present_tag), None
                return TagPresent(tag=tag_id), "set"
            # No tag, distinguish micro-interruption from long reader absence.
            # gap uses last_event_timestamp because removed_at isn't recorded yet;
            # a large gap means the reader was off for a while, not a brief NFC miss.
            gap = timestamp - (state.last_event_timestamp or timestamp)
            if gap < ctx.grace_seconds:
                return TagRemoved(tag=present_tag, removed_at=timestamp), None
            return NoTag(), "clear"

        case TagRemoved(tag=removed_tag, removed_at=removed_at):
            if tag_id is not None:
                if tag_id == removed_tag:
                    return TagPresent(tag=removed_tag), None
                return TagPresent(tag=tag_id), "set"
            removal_duration = timestamp - removed_at
            if removal_duration < ctx.grace_seconds:
                return state, None
            return NoTag(), "clear"
