from pydantic import BaseModel


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
