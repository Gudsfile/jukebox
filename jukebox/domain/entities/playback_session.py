from pydantic import BaseModel

from .playback_action import PlaybackAction


class PlaybackCommandRetry(BaseModel):
    """Tracks retry timing for a failed playback command."""

    action: PlaybackAction
    command_key: str
    first_failed_at: float
    last_failed_at: float
    attempt_count: int
    next_retry_at: float | None
    exhausted: bool = False


class PlaybackSession(BaseModel):
    """Tracks the current logical playback and physical reader states."""

    # Logical playback state
    playing_tag: str | None = None
    paused_at: float | None = None
    playing_tag_removed_at: float | None = None

    # Physical reader state
    physical_tag: str | None = None
    physical_tag_removed_at: float | None = None

    # Timestamp
    last_event_timestamp: float | None = None

    # Playback command retry state
    playback_command_retry: PlaybackCommandRetry | None = None
