from __future__ import annotations

import json

import pytest

from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.domain.entities import Disc, DiscMetadata, DiscOption, Library


def write_library(filepath, library: Library | dict) -> None:
    data = library.model_dump() if isinstance(library, Library) else library
    with open(filepath, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, indent=2, ensure_ascii=False)


def read_library(filepath) -> dict:
    with open(filepath, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def test_list_discs_returns_existing_library(tmp_path):
    filepath = tmp_path / "library.json"
    write_library(
        filepath,
        Library(
            discs={
                "tag:123": Disc(
                    uri="uri:456",
                    metadata=DiscMetadata(artist="Test Artist"),
                    option=DiscOption(shuffle=False, is_test=False),
                )
            }
        ),
    )

    adapter = JsonLibraryAdapter(str(filepath))
    discs = adapter.list_discs()

    assert "tag:123" in discs
    assert discs["tag:123"].uri == "uri:456"
    assert discs["tag:123"].metadata.artist == "Test Artist"


def test_list_discs_returns_empty_when_file_does_not_exist(tmp_path):
    adapter = JsonLibraryAdapter(str(tmp_path / "missing-library.json"))

    assert adapter.list_discs() == {}


def test_list_discs_returns_empty_when_json_is_corrupted(tmp_path):
    filepath = tmp_path / "library.json"
    filepath.write_text("{invalid json content", encoding="utf-8")

    adapter = JsonLibraryAdapter(str(filepath))

    assert adapter.list_discs() == {}


def test_list_discs_returns_empty_when_schema_is_invalid(tmp_path):
    filepath = tmp_path / "library.json"
    write_library(filepath, {"invalid": "schema"})

    adapter = JsonLibraryAdapter(str(filepath))

    assert adapter.list_discs() == {}


def test_get_disc_uses_cache_when_file_is_unchanged(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="test.mp3", metadata=DiscMetadata())}))
    adapter = JsonLibraryAdapter(str(filepath))
    load_spy = mocker.spy(adapter, "_load_from_disk")

    first_result = adapter.get_disc("test-tag")
    second_result = adapter.get_disc("test-tag")

    assert first_result == Disc(uri="test.mp3", metadata=DiscMetadata())
    assert second_result == first_result
    assert load_spy.call_count == 1


def test_external_file_changes_invalidate_cache(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="before.mp3", metadata=DiscMetadata())}))
    adapter = JsonLibraryAdapter(str(filepath))
    load_spy = mocker.spy(adapter, "_load_from_disk")

    assert adapter.get_disc("test-tag").uri == "before.mp3"

    write_library(
        filepath,
        Library(
            discs={
                "test-tag": Disc(uri="after.mp3", metadata=DiscMetadata(artist="Updated Artist")),
                "another-tag": Disc(uri="extra.mp3", metadata=DiscMetadata()),
            }
        ),
    )

    updated_disc = adapter.get_disc("test-tag")

    assert updated_disc is not None
    assert updated_disc.uri == "after.mp3"
    assert updated_disc.metadata.artist == "Updated Artist"
    assert load_spy.call_count == 2


def test_list_discs_returns_copies_not_live_cached_state(tmp_path):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="original.mp3", metadata=DiscMetadata())}))
    adapter = JsonLibraryAdapter(str(filepath))

    discs = adapter.list_discs()
    discs["test-tag"].uri = "mutated.mp3"
    discs["new-tag"] = Disc(uri="phantom.mp3", metadata=DiscMetadata())

    fresh_disc = adapter.get_disc("test-tag")

    assert fresh_disc is not None
    assert fresh_disc.uri == "original.mp3"
    assert adapter.get_disc("new-tag") is None


def test_add_disc_persists_and_updates_cache(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    adapter = JsonLibraryAdapter(str(filepath))
    load_spy = mocker.spy(adapter, "_load_from_disk")
    new_disc = Disc(uri="new.mp3", metadata=DiscMetadata(artist="Artist"))

    adapter.add_disc("new-tag", new_disc)

    assert adapter.get_disc("new-tag") == new_disc
    assert read_library(filepath)["discs"]["new-tag"]["uri"] == "new.mp3"
    assert load_spy.call_count == 1


def test_edit_disc_persists_and_updates_cache(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(
        filepath,
        Library(
            discs={
                "test-tag": Disc(
                    uri="before.mp3",
                    metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
                    option=DiscOption(shuffle=False),
                )
            }
        ),
    )
    adapter = JsonLibraryAdapter(str(filepath))
    load_spy = mocker.spy(adapter, "_load_from_disk")

    adapter.edit_disc(
        "test-tag",
        uri="after.mp3",
        metadata=DiscMetadata(track="Updated Track"),
        option=DiscOption(shuffle=True),
    )

    updated_disc = adapter.get_disc("test-tag")

    assert updated_disc == Disc(
        uri="after.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=True),
    )
    assert read_library(filepath)["discs"]["test-tag"]["option"]["shuffle"] is True
    assert load_spy.call_count == 1


def test_remove_disc_persists_and_updates_cache(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="test.mp3", metadata=DiscMetadata())}))
    adapter = JsonLibraryAdapter(str(filepath))
    load_spy = mocker.spy(adapter, "_load_from_disk")

    adapter.remove_disc("test-tag")

    assert adapter.get_disc("test-tag") is None
    assert read_library(filepath)["discs"] == {}
    assert load_spy.call_count == 1


def test_search_discs_matches_tag_and_metadata(tmp_path):
    filepath = tmp_path / "library.json"
    write_library(
        filepath,
        Library(
            discs={
                "tag:pink:floyd": Disc(uri="uri1", metadata=DiscMetadata(artist="Pink Floyd")),
                "tag:other": Disc(uri="uri2", metadata=DiscMetadata(album="Not Pink")),
            }
        ),
    )
    adapter = JsonLibraryAdapter(str(filepath))

    results = adapter.search_discs("pink")

    assert set(results) == {"tag:pink:floyd", "tag:other"}


def test_add_disc_raises_for_duplicate_tag(tmp_path):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="test.mp3", metadata=DiscMetadata())}))
    adapter = JsonLibraryAdapter(str(filepath))

    with pytest.raises(ValueError, match="Already existing tag: tag_id='test-tag'"):
        adapter.add_disc("test-tag", Disc(uri="new.mp3", metadata=DiscMetadata()))


def test_edit_disc_raises_for_missing_tag(tmp_path):
    adapter = JsonLibraryAdapter(str(tmp_path / "library.json"))

    with pytest.raises(ValueError, match="Tag does not exist: tag_id='missing-tag'"):
        adapter.edit_disc("missing-tag", uri="new.mp3")


def test_remove_disc_raises_for_missing_tag(tmp_path):
    adapter = JsonLibraryAdapter(str(tmp_path / "library.json"))

    with pytest.raises(ValueError, match="Tag does not exist: tag_id='missing-tag'"):
        adapter.remove_disc("missing-tag")


def test_failed_write_during_add_disc_does_not_leak_phantom_state(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    adapter = JsonLibraryAdapter(str(filepath))

    assert adapter.list_discs() == {}

    mocker.patch.object(adapter, "_write_library", side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"):
        adapter.add_disc("phantom-tag", Disc(uri="phantom.mp3", metadata=DiscMetadata()))

    assert adapter.get_disc("phantom-tag") is None
    assert adapter.list_discs() == {}


def test_failed_write_during_edit_disc_does_not_leak_partial_state(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="before.mp3", metadata=DiscMetadata(artist="Artist"))}))
    adapter = JsonLibraryAdapter(str(filepath))

    original_disc = adapter.get_disc("test-tag")
    mocker.patch.object(adapter, "_write_library", side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"):
        adapter.edit_disc("test-tag", uri="after.mp3", metadata=DiscMetadata(track="Updated Track"))

    assert adapter.get_disc("test-tag") == original_disc


def test_failed_write_during_remove_disc_does_not_hide_on_disk_state(tmp_path, mocker):
    filepath = tmp_path / "library.json"
    write_library(filepath, Library(discs={"test-tag": Disc(uri="before.mp3", metadata=DiscMetadata(artist="Artist"))}))
    adapter = JsonLibraryAdapter(str(filepath))

    original_disc = adapter.get_disc("test-tag")
    mocker.patch.object(adapter, "_write_library", side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"):
        adapter.remove_disc("test-tag")

    assert adapter.get_disc("test-tag") == original_disc
