from pydantic import BaseModel


class TagEvent(BaseModel):
    """Represents a tag detection event from the reader."""

    tag_id: str | None  # None if no tag detected
    timestamp: float
