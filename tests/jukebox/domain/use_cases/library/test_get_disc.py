import pytest

from jukebox.domain.entities import Disc, DiscMetadata, Library
from jukebox.domain.use_cases.library.get_disc import GetDisc
from tests.jukebox.domain.use_cases.library.mock_repo import MockRepo


def test_get_existing_disc():
    repo = MockRepo(
        Library(discs={"tag:123": Disc(uri="uri:1", metadata=DiscMetadata(artist="artist", album="album"))})
    )

    get_disc = GetDisc(repo)
    result = get_disc.execute("tag:123")

    assert repo.get_calls == ["tag:123"]
    assert result.uri == "uri:1"
    assert result.metadata.artist == "artist"
    assert result.metadata.album == "album"


def test_get_nonexistent_disc_raises_error():
    repo = MockRepo(Library(discs={}))

    get_disc = GetDisc(repo)
    with pytest.raises(ValueError, match="Tag not found"):
        get_disc.execute("nonexistent")

    assert repo.get_calls == ["nonexistent"]
