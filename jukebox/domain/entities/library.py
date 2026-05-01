from pydantic import BaseModel, ConfigDict, Field

from jukebox.domain.entities import Disc


class Library(BaseModel):
    """A library containing a collection of discs indexed by tag ID."""

    model_config = ConfigDict(strict=True)
    discs: dict[str, Disc] = Field(default={}, description="Correspondences between tags and discs")
