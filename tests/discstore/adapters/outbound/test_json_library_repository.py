import json
import os
import tempfile

from discstore.adapters.outbound.json_library_repository import JsonLibraryRepository
from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library


class TestJsonLibraryRepository:
    """Tests for JsonLibraryRepository"""

    def test_load_existing_library(self):
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
            repo = JsonLibraryRepository(filepath)
            library = repo.load()
            assert "tag:123" in library.discs
            assert library.discs["tag:123"].uri == "uri:456"
            assert library.discs["tag:123"].metadata.artist == "Test Artist"
        finally:
            os.unlink(filepath)

    def test_load_nonexistent_file_returns_empty_library(self):
        """Should return empty library when file doesn't exist"""
        repo = JsonLibraryRepository("/nonexistent/path/library.json")
        library = repo.load()
        assert isinstance(library, Library)
        assert len(library.discs) == 0

    def test_load_corrupted_json_returns_empty_library(self):
        """Should return empty library when JSON is corrupted"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("{invalid json content")
            filepath = f.name

        try:
            repo = JsonLibraryRepository(filepath)
            library = repo.load()
            assert isinstance(library, Library)
            assert len(library.discs) == 0
        finally:
            os.unlink(filepath)

    def test_load_invalid_schema_returns_empty_library(self):
        """Should return empty library when schema is invalid"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({"invalid": "schema"}, f)
            filepath = f.name

        try:
            repo = JsonLibraryRepository(filepath)
            library = repo.load()
            assert isinstance(library, Library)
            assert len(library.discs) == 0
        finally:
            os.unlink(filepath)

    def test_save_library(self):
        """Should save library to JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            filepath = f.name

        try:
            repo = JsonLibraryRepository(filepath)
            library = Library(discs={"tag:123": Disc(uri="uri:456", metadata=DiscMetadata(artist="Test Artist"))})
            repo.save(library)

            # Verify file was written correctly
            with open(filepath, "r") as f:
                data = json.load(f)
            assert "discs" in data
            assert "tag:123" in data["discs"]
            assert data["discs"]["tag:123"]["uri"] == "uri:456"
        finally:
            os.unlink(filepath)

    def test_save_and_load_roundtrip(self):
        """Should preserve data through save and load cycle"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            filepath = f.name

        try:
            repo = JsonLibraryRepository(filepath)
            original_library = Library(
                discs={
                    "tag:123": Disc(uri="uri:789", metadata=DiscMetadata(artist="Artist", album="Album", track="Track"))
                }
            )
            repo.save(original_library)
            loaded_library = repo.load()

            assert loaded_library.discs.keys() == original_library.discs.keys()
            assert loaded_library.discs["tag:123"].uri == original_library.discs["tag:123"].uri
            assert loaded_library.discs["tag:123"].metadata.artist == original_library.discs["tag:123"].metadata.artist
        finally:
            os.unlink(filepath)
