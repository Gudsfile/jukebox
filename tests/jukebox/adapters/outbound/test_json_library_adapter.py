from unittest.mock import MagicMock

from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.entities.library import Library
from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter


def test_get_disc_returns_disc_when_exists():
    """Should return disc when it exists in library."""
    adapter = JsonLibraryAdapter("/fake/path.json")

    mock_repo = MagicMock()
    test_disc = Disc(uri="test.mp3", metadata=DiscMetadata(), option=DiscOption())
    mock_repo.load.return_value = Library(discs={"test-tag": test_disc})
    adapter.repository = mock_repo

    result = adapter.get_disc("test-tag")

    assert result == test_disc
    mock_repo.load.assert_called_once()


def test_get_disc_returns_none_when_not_exists():
    """Should return None when disc doesn't exist in library."""
    adapter = JsonLibraryAdapter("/fake/path.json")

    mock_repo = MagicMock()
    mock_repo.load.return_value = Library(discs={})
    adapter.repository = mock_repo

    result = adapter.get_disc("nonexistent-tag")

    assert result is None
    mock_repo.load.assert_called_once()
