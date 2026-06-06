import sys
from io import StringIO

import pytest
from rich.console import Console

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
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True, width=200)
    display_library_table(sample_discs, console=console)
    output = buf.getvalue()

    assert "Discs Library" in output
    assert "abc123" in output
    assert "xyz789" in output
    assert "/path/to/music.mp3" in output
    assert "Test Artist" in output
    assert "Another Artist" in output
    assert "ID" in output
    assert "URI" in output
