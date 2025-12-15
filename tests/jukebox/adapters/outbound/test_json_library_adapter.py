import json
import os
import tempfile

from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.domain.entities import Disc, DiscMetadata, DiscOption, Library


def test_load_existing_library():
    """Should load existing library from JSON file"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(
            {
                "discs": {
                    "tag:123": {
                        "uri": "uri:456",
                        "metadata": {"artist": "Test Artist"},
                        "option": {"shuffle": False, "is_test": False},
                    }
                }
            },
            f,
        )
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        library = adapter.load()
        assert "tag:123" in library.discs
        assert library.discs["tag:123"].uri == "uri:456"
        assert library.discs["tag:123"].metadata.artist == "Test Artist"
    finally:
        os.unlink(filepath)


def test_load_nonexistent_file_returns_empty_library():
    """Should return empty library when file doesn't exist"""
    adapter = JsonLibraryAdapter("/nonexistent/path/library.json")
    library = adapter.load()
    assert isinstance(library, Library)
    assert len(library.discs) == 0


def test_load_corrupted_json_returns_empty_library():
    """Should return empty library when JSON is corrupted"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("{invalid json content")
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        library = adapter.load()
        assert isinstance(library, Library)
        assert len(library.discs) == 0
    finally:
        os.unlink(filepath)


def test_load_invalid_schema_returns_empty_library():
    """Should return empty library when schema is invalid"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump({"invalid": "schema"}, f)
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        library = adapter.load()
        assert isinstance(library, Library)
        assert len(library.discs) == 0
    finally:
        os.unlink(filepath)


def test_save_library():
    """Should save library to JSON file"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        library = Library(discs={"tag:123": Disc(uri="uri:456", metadata=DiscMetadata(artist="Test Artist"))})
        adapter.save(library)

        # Verify file was written correctly
        with open(filepath, "r") as f:
            data = json.load(f)
        assert "discs" in data
        assert "tag:123" in data["discs"]
        assert data["discs"]["tag:123"]["uri"] == "uri:456"
    finally:
        os.unlink(filepath)


def test_save_and_load_roundtrip():
    """Should preserve data through save and load cycle"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        original_library = Library(
            discs={"tag:123": Disc(uri="uri:789", metadata=DiscMetadata(artist="Artist", album="Album", track="Track"))}
        )
        adapter.save(original_library)
        loaded_library = adapter.load()

        assert loaded_library.discs.keys() == original_library.discs.keys()
        assert loaded_library.discs["tag:123"].uri == original_library.discs["tag:123"].uri
        assert loaded_library.discs["tag:123"].metadata.artist == original_library.discs["tag:123"].metadata.artist
    finally:
        os.unlink(filepath)


def test_get_disc_returns_disc_when_exists():
    """Should return disc when it exists in library."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    test_disc = Disc(uri="test.mp3", metadata=DiscMetadata(), option=DiscOption())

    try:
        adapter = JsonLibraryAdapter(filepath)
        original_library = Library(
            discs={
                "test-tag": test_disc,
                "another-tag": Disc(uri="another.mp3", metadata=DiscMetadata(), option=DiscOption()),
            }
        )
        adapter.save(original_library)
        result = adapter.get_disc("test-tag")

        assert result == test_disc
    finally:
        os.unlink(filepath)


def test_get_disc_returns_none_when_not_exists():
    """Should return None when disc doesn't exist in library."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        adapter = JsonLibraryAdapter(filepath)
        original_library = Library(
            discs={"another-tag": Disc(uri="another.mp3", metadata=DiscMetadata(), option=DiscOption())}
        )
        adapter.save(original_library)
        result = adapter.get_disc("test-tag")

        assert result is None
    finally:
        os.unlink(filepath)
