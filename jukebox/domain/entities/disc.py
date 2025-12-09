from typing import Optional

from pydantic import BaseModel, Field


class DiscOption(BaseModel):
    """Playback options for a disc."""

    shuffle: bool = Field(default=False, description="Enable or disable shuffle playback")
    is_test: bool = Field(default=False, description="Indicates whether this is a test disc")


class DiscMetadata(BaseModel):
    """Metadata information for a disc."""

    artist: Optional[str] = Field(default=None, description="Name of the artist or band", examples=["Zubi", None])
    album: Optional[str] = Field(default=None, description="Name of the album", examples=["Dear Z", None])
    track: Optional[str] = Field(default=None, description="Name of the track", examples=["dey ok", None])
    playlist: Optional[str] = Field(default=None, description="Name of the playlist", examples=["dey ok", None])


class Disc(BaseModel):
    """A disc entity representing a music item with metadata and playback options."""

    uri: str = Field(description="Path or URI of the media file", examples=["spotify:album:3IvUwbVgAZSqNh06PVxwG7"])
    option: DiscOption = Field(default=DiscOption(), description="Playback options for the disc")
    metadata: DiscMetadata = Field(description="Metadata associated with the disc")
