from pydantic import BaseModel


class CurrentDisc(BaseModel):
    """Shared state for the tag that is physically present on the reader."""

    tag_id: str
    known_in_library: bool
