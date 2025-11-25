from typing import Optional

from pydantic import BaseModel


class PlaybackSession(BaseModel):
    """Tracks the current playback state."""

    current_tag: Optional[str] = None
    previous_tag: Optional[str] = None
    awaiting_seconds: float = 0.0
    tag_removed_seconds: float = 0.0
    is_paused: bool = False
