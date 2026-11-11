from pydantic import BaseModel, Field, field_validator


class DiscOption(BaseModel):
    """Playback options for a disc."""

    shuffle: bool = Field(default=False, description="Enable or disable shuffle playback")


class DiscMetadata(BaseModel):
    """Metadata information for a disc."""

    artist: str | None = Field(default=None, description="Name of the artist or band", examples=["Zubi", None])
    album: str | None = Field(default=None, description="Name of the album", examples=["Dear Z", None])
    track: str | None = Field(default=None, description="Name of the track", examples=["dey ok", None])
    playlist: str | None = Field(default=None, description="Name of the playlist", examples=["dey ok", None])

    @field_validator("artist", "album", "track", "playlist", mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        """Store "no value" as None, whichever client sent it (empty UI field, `--artist ""`, old library.json)."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def has_title(self) -> bool:
        return bool(self.playlist or self.track or self.album or self.artist)

    @property
    def display_title(self) -> str:
        if self.playlist:
            owner = f" ({self.artist})" if self.artist else ""
            return f"{self.playlist}{owner}"
        subject = self.track or self.album
        if subject and self.artist:
            return f"{self.artist} — {subject}"
        return subject or self.artist or "—"

    @property
    def display_type(self) -> str:
        if self.playlist:
            return "\U0001f3a7 Playlist"
        if self.track:
            return "\U0001f3b5 Track"
        if self.artist and not self.album:
            return "\U0001f3a4 Artist"
        return "\U0001f4bf Album"


class Disc(BaseModel):
    """A disc entity representing a music item with metadata and playback options."""

    uri: str = Field(description="Path or URI of the media file", examples=["spotify:album:3IvUwbVgAZSqNh06PVxwG7"])
    option: DiscOption = Field(default=DiscOption(), description="Playback options for the disc")
    metadata: DiscMetadata = Field(default_factory=DiscMetadata, description="Metadata associated with the disc")
