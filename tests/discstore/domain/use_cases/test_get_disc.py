import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.use_cases.get_disc import GetDisc
from tests.discstore.domain.use_cases.mock_repo import MockRepo


def test_get_existing_disc():
    repo = MockRepo(
        Library(discs={"tag:123": Disc(uri="uri:1", metadata=DiscMetadata(artist="artist", album="album"))})
    )

    get_disc = GetDisc(repo)
    result = get_disc.execute("tag:123")

    assert result.uri == "uri:1"
    assert result.metadata.artist == "artist"
    assert result.metadata.album == "album"


def test_get_nonexistent_disc_raises_error():
    repo = MockRepo(Library(discs={}))

    get_disc = GetDisc(repo)
    with pytest.raises(ValueError, match="Tag not found"):
        get_disc.execute("nonexistent")
