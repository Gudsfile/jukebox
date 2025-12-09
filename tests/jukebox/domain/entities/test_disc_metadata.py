from discstore.domain.entities import DiscMetadata


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
