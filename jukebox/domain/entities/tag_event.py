from typing import Optional

from pydantic import BaseModel


class TagEvent(BaseModel):
    """Represents a tag detection event from the reader."""

    tag_id: Optional[str]  # None if no tag detected
    timestamp: float
