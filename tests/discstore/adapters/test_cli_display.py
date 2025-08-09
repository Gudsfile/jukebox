import sys
from io import StringIO
from typing import Dict

import pytest

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption


@pytest.fixture
def sample_discs() -> Dict[str, Disc]:
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
        == """=== CDs Library ===

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
    output = capture_output(display_library_table, sample_discs).split("\n")
    assert len(output) == 5
    assert output[0] == "ID     | URI                | Artist         | Album      | Track      | Playlist | Shuffle"  # fmt: skip
    assert output[1] == "-------+--------------------+----------------+------------+------------+----------+--------"  # fmt: skip
    assert output[2] == "abc123 | /path/to/music.mp3 | Test Artist    | Test Album | Test Track | /        | True   "  # fmt: skip
    assert output[3] == "xyz789 | /another/track.mp3 | Another Artist | /          | /          | /        | False  "  # fmt: skip
    assert output[4] == ""
