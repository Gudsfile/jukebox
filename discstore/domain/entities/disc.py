from typing import Optional

from pydantic import BaseModel, Field


class DiscOption(BaseModel):
    shuffle: bool = Field(default=False, description="Enable or disable shuffle playback")
    is_test: bool = Field(default=False, description="Indicates whether this is a test disc")


class DiscMetadata(BaseModel):
    artist: Optional[str] = Field(default=None, description="Name of the artist or band", examples=["Zubi", None])
    album: Optional[str] = Field(default=None, description="Name of the album", examples=["Dear Z", None])
    track: Optional[str] = Field(default=None, description="Name of the track", examples=["dey ok", None])
    playlist: Optional[str] = Field(default=None, description="Name of the playlist", examples=["dey ok", None])


class Disc(BaseModel):
    uri: str = Field(description="Path or URI of the media file", examples=["spotify:track:5yYCqkCxYnXFLqApA98Ltv"])
    option: DiscOption = Field(default=DiscOption(), description="Playback options for the disc")
    metadata: DiscMetadata = Field(description="Metadata associated with the disc")
