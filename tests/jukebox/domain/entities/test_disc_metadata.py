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
        pytest.param("playlist", "artist", None, None, "playlist (artist)", id="playlist+artist"),
        pytest.param("playlist", None, None, None, "playlist", id="playlist"),
        pytest.param("playlist", "artist", "album", "track", "playlist (artist)", id="playlist+artist+album+track"),
        pytest.param(None, "artist", "album", None, "artist — album", id="artist+album"),
        pytest.param(None, "artist", None, "track", "artist — track", id="artist+track"),
        pytest.param(None, "artist", "album", "track", "artist — track", id="artist+album+track"),
        pytest.param(None, "artist", None, None, "artist", id="artist"),
        pytest.param(None, None, "album", None, "album", id="album"),
        pytest.param(None, None, "album", "track", "track", id="album+track"),
        pytest.param(None, None, None, "track", "track", id="track"),
        pytest.param(None, None, None, None, "—", id="empty"),
    ],
)
def test_display_title(playlist, artist, album, track, expected):
    metadata = DiscMetadata(playlist=playlist, artist=artist, album=album, track=track)
    assert metadata.display_title == expected


@pytest.mark.parametrize(
    ("playlist", "artist", "album", "track", "expected"),
    [
        pytest.param("playlist", None, None, None, "🎧 Playlist", id="playlist"),
        pytest.param("playlist", "artist", "album", "track", "🎧 Playlist", id="playlist+artist+album+track"),
        pytest.param(None, "artist", None, None, "🎤 Artist", id="artist"),
        pytest.param(None, "artist", None, "track", "🎵 Track", id="artist+track"),
        pytest.param(None, None, None, "track", "🎵 Track", id="track"),
        pytest.param(None, "artist", "album", None, "💿 Album", id="artist+album"),
        pytest.param(None, "artist", "album", "track", "🎵 Track", id="artist+album+track"),
        pytest.param(None, None, "album", "track", "🎵 Track", id="album+track"),
        pytest.param(None, None, None, None, "💿 Album", id="empty"),
    ],
)
def test_display_type(playlist, artist, album, track, expected):
    metadata = DiscMetadata(playlist=playlist, artist=artist, album=album, track=track)
    assert metadata.display_type == expected
