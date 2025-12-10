import pytest
from pydantic import ValidationError

from discstore.domain.entities import Disc, DiscMetadata, DiscOption


def test_minimal_disc():
    """Should create disc with only URI"""
    disc = Disc(uri="uri:123", metadata=DiscMetadata())
    assert disc.uri == "uri:123"
    assert disc.option.shuffle is False
    assert disc.metadata.artist is None


def test_disc_with_metadata():
    """Should create disc with metadata"""
    metadata = DiscMetadata(artist="artist", album="album")
    disc = Disc(uri="uri:456", metadata=metadata)
    assert disc.uri == "uri:456"
    assert disc.metadata.artist == "artist"
    assert disc.metadata.album == "album"


def test_disc_with_options():
    """Should create disc with options"""
    option = DiscOption(shuffle=True)
    disc = Disc(uri="uri:789", metadata=DiscMetadata(), option=option)
    assert disc.uri == "uri:789"
    assert disc.option.shuffle is True


def test_uri_required():
    """URI should be required"""
    with pytest.raises(ValidationError):
        Disc(metadata=DiscMetadata())  # ty: ignore[missing-argument]


def test_metadata_required():
    """Metadata should be required"""
    with pytest.raises(ValidationError):
        Disc(uri="uri:123")  # ty: ignore[missing-argument]


def test_empty_strings_in_metadata():
    """Should accept empty strings in metadata"""
    metadata = DiscMetadata(artist="", album="")
    disc = Disc(uri="uri:123", metadata=metadata)
    assert disc.metadata.artist == ""
    assert disc.metadata.album == ""
