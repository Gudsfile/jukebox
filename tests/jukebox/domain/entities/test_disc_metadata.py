import pytest

from jukebox.domain.entities import DiscMetadata


def test_all_fields_optional():
    """All metadata fields should be optional"""
    metadata = DiscMetadata()
    assert metadata.artist is None
    assert metadata.album is None
    assert metadata.track is None
    assert metadata.playlist is None


def test_partial_metadata():
    """Should accept partial metadata"""
    metadata = DiscMetadata(artist="artist", album="album")
    assert metadata.artist == "artist"
    assert metadata.album == "album"
    assert metadata.track is None
    assert metadata.playlist is None


def test_full_metadata():
    """Should accept all metadata fields"""
    metadata = DiscMetadata(artist="artist", album="album", track="track", playlist="playlist")
    assert metadata.artist == "artist"
    assert metadata.album == "album"
    assert metadata.track == "track"
    assert metadata.playlist == "playlist"


@pytest.mark.parametrize(
    ("playlist", "artist", "album", "track", "expected"),
    [
        ("playlist", "artist", None, None, "playlist (artist)"),
        ("playlist", None, None, None, "playlist"),
        (None, "artist", "album", None, "artist — album"),
        (None, "artist", None, None, "artist"),
        (None, None, "album", None, "album"),
        (None, None, None, "track", "track"),
        (None, None, None, None, "—"),
    ],
)
def test_display_title(playlist, artist, album, track, expected):
    metadata = DiscMetadata(playlist=playlist, artist=artist, album=album, track=track)
    assert metadata.display_title == expected


@pytest.mark.parametrize(
    ("playlist", "expected"),
    [
        ("My Mix", "🎧 Playlist"),
        (None, "💿 Album"),
    ],
)
def test_display_type(playlist, expected):
    metadata = DiscMetadata(playlist=playlist)
    assert metadata.display_type == expected
