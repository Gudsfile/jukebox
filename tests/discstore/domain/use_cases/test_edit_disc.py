import pytest

from discstore.domain.entities import Disc, DiscMetadata, DiscOption, Library
from discstore.domain.use_cases.edit_disc import EditDisc

from .mock_repo import MockRepo


def test_edit_only_uri():
    original_disc = Disc(
        uri="uri:old",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    repo = MockRepo(Library(discs={"tag:123": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:123", uri="uri:new")

    library = repo.load()
    updated_disc = library.discs["tag:123"]
    assert updated_disc.uri == "uri:new"
    assert updated_disc.metadata.artist == "Artist"
    assert updated_disc.metadata.album == "Album"
    assert updated_disc.metadata.track == "Track"
    assert updated_disc.option.shuffle is True


def test_edit_only_track_name():
    original_disc = Disc(
        uri="uri:123",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Old Track"),
        option=DiscOption(),
    )
    repo = MockRepo(Library(discs={"tag:456": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:456", metadata=DiscMetadata(track="New Track"))

    library = repo.load()
    updated_disc = library.discs["tag:456"]
    assert updated_disc.uri == "uri:123"
    assert updated_disc.metadata.artist == "Artist"
    assert updated_disc.metadata.album == "Album"
    assert updated_disc.metadata.track == "New Track"


def test_edit_only_artist():
    original_disc = Disc(uri="uri:789", metadata=DiscMetadata(artist="Old Artist", album="Album"), option=DiscOption())
    repo = MockRepo(Library(discs={"tag:789": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:789", metadata=DiscMetadata(artist="New Artist"))

    library = repo.load()
    updated_disc = library.discs["tag:789"]
    assert updated_disc.metadata.artist == "New Artist"
    assert updated_disc.metadata.album == "Album"
    assert updated_disc.metadata.track is None


def test_edit_multiple_metadata_fields():
    original_disc = Disc(
        uri="uri:abc",
        metadata=DiscMetadata(artist="Old Artist", album="Old Album", track="Old Track"),
        option=DiscOption(),
    )
    repo = MockRepo(Library(discs={"tag:abc": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:abc", metadata=DiscMetadata(artist="New Artist", track="New Track"))

    library = repo.load()
    updated_disc = library.discs["tag:abc"]
    assert updated_disc.metadata.artist == "New Artist"
    assert updated_disc.metadata.track == "New Track"


def test_edit_uri_and_metadata():
    original_disc = Disc(uri="uri:old", metadata=DiscMetadata(artist="Old Artist"), option=DiscOption())
    repo = MockRepo(Library(discs={"tag:xyz": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:xyz", uri="uri:new", metadata=DiscMetadata(artist="New Artist", album="New Album"))

    library = repo.load()
    updated_disc = library.discs["tag:xyz"]
    assert updated_disc.uri == "uri:new"
    assert updated_disc.metadata.artist == "New Artist"
    assert updated_disc.metadata.album == "New Album"


def test_edit_options():
    original_disc = Disc(uri="uri:123", metadata=DiscMetadata(playlist="My Playlist"), option=DiscOption(shuffle=False))
    repo = MockRepo(Library(discs={"tag:opt": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:opt", option=DiscOption(shuffle=True))

    library = repo.load()
    updated_disc = library.discs["tag:opt"]
    assert updated_disc.uri == "uri:123"
    assert updated_disc.metadata.playlist == "My Playlist"
    assert updated_disc.option.shuffle is True


def test_edit_nonexistent_tag_raises_error():
    repo = MockRepo(Library(discs={}))

    edit_disc = EditDisc(repo)
    with pytest.raises(ValueError, match="Tag does not exist: tag_id='nonexistent'"):
        edit_disc.execute(tag_id="nonexistent", uri="uri:123")

    assert repo.saved_library is None


def test_edit_with_no_changes():
    original_disc = Disc(uri="uri:123", metadata=DiscMetadata(artist="Artist"), option=DiscOption())
    repo = MockRepo(Library(discs={"tag:noop": original_disc}))

    edit_disc = EditDisc(repo)
    edit_disc.execute(tag_id="tag:noop", uri=None, metadata=None, option=None)

    library = repo.load()
    updated_disc = library.discs["tag:noop"]
    assert updated_disc.uri == "uri:123"
    assert updated_disc.metadata.artist == "Artist"
