from pydantic import BaseModel


class CurrentTagSession(BaseModel):
    """Tracks the physical NFC reader state for the current-tag feature."""

    physical_tag: str | None = None
    physical_tag_removed_at: float | None = None
    # Stamped by SyncCurrentTag.execute in a finally block; None only before the first call.
    last_event_timestamp: float | None = None
