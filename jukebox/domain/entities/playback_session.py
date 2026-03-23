from typing import Optional

from pydantic import BaseModel


class PlaybackSession(BaseModel):
    """Tracks the current logical playback and physical reader states."""

    # Logical playback state
    playing_tag: Optional[str] = None
    is_paused: bool = False
    pause_duration_seconds: float = 0.0
    playing_tag_removed_at: Optional[float] = None

    # Physical reader state
    physical_tag: Optional[str] = None
    physical_tag_removed_at: Optional[float] = None

    # Timestamp
    last_event_timestamp: Optional[float] = None
