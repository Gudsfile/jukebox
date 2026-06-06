import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from rich.table import Table

from jukebox.adapters.inbound.admin.cli_display import display_library_line, display_library_table
from jukebox.domain.entities import Disc, DiscMetadata, DiscOption


@pytest.fixture
def sample_discs() -> dict[str, Disc]:
    return {
        "abc123": Disc(
            uri="/path/to/music.mp3",
            option=DiscOption(shuffle=True),
            metadata=DiscMetadata(artist="Test Artist", album="Test Album", track="Test Track"),
        ),
        "xyz789": Disc(uri="/another/track.mp3", metadata=DiscMetadata(artist="Another Artist")),
    }


def capture_output(func, *args, **kwargs):
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        func(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def test_display_library_line(sample_discs):
    output = capture_output(display_library_line, sample_discs)
    assert (
        output
        == """=== Discs Library ===

ID : abc123
  URI      : /path/to/music.mp3
  Artist   : Test Artist
  Album    : Test Album
  Track    : Test Track
  Playlist : /
  Shuffle  : True
------------------------------
ID : xyz789
  URI      : /another/track.mp3
  Artist   : Another Artist
  Album    : /
  Track    : /
  Playlist : /
  Shuffle  : False
------------------------------
"""
    )


def test_display_library_table(sample_discs):
    with patch("jukebox.adapters.inbound.admin.cli_display.Console") as mock_console_cls:
        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console
        display_library_table(sample_discs)

    mock_console.print.assert_called_once()
    table = mock_console.print.call_args[0][0]

    assert isinstance(table, Table)
    assert table.title == "Discs Library"
    assert table.row_count == 2
    assert [col.header for col in table.columns] == ["ID", "URI", "Artist", "Album", "Track", "Playlist", "Shuffle"]
    assert list(table.columns[0]._cells) == ["abc123", "xyz789"]
    assert list(table.columns[1]._cells) == ["/path/to/music.mp3", "/another/track.mp3"]
    assert list(table.columns[2]._cells) == ["Test Artist", "Another Artist"]
