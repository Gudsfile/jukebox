import sys
from io import StringIO

import pytest
from rich.cells import cell_len
from rich.console import Console

from jukebox.adapters.inbound.admin.cli_display import (
    DISC_FIELDS,
    TABLE_DROP_ORDER,
    build_remove_confirmation,
    display_disc,
    display_library_line,
    display_library_table,
)
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


@pytest.fixture
def console_capture() -> tuple[Console, StringIO]:
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True, width=200)
    return console, buf


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
  Type     : 🎵 Track
  Title    : Test Artist — Test Track
  URI      : /path/to/music.mp3
  Artist   : Test Artist
  Album    : Test Album
  Track    : Test Track
  Playlist : /
  Shuffle  : True
------------------------------
ID : xyz789
  Type     : 🎤 Artist
  Title    : Another Artist
  URI      : /another/track.mp3
  Artist   : Another Artist
  Album    : /
  Track    : /
  Playlist : /
  Shuffle  : False
------------------------------
"""
    )


def test_display_library_table_empty(console_capture):
    console, buf = console_capture
    display_library_table({}, console=console)
    assert "The library is empty" in buf.getvalue()


def test_display_library_table(sample_discs, console_capture):
    console, buf = console_capture
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
    assert "Type" in output
    assert "Title" in output
    assert "🎵 Track" in output
    assert "🎤 Artist" in output
    assert "Test Artist — Test Track" in output


def test_display_disc(sample_discs, console_capture):
    disc = sample_discs["abc123"]
    console, buf = console_capture
    display_disc("abc123", disc, console=console)
    output = buf.getvalue()

    assert "📀 Disc: abc123" in output
    assert "/path/to/music.mp3" in output
    assert "Test Artist" in output
    assert "Test Album" in output
    assert "Test Track" in output
    assert "Playlist : /" in output
    assert "True" in output
    assert "Type     : 🎵 Track" in output
    assert "Title    : Test Artist — Test Track" in output


def test_display_disc_shows_fallback_for_missing_metadata(console_capture):
    disc = Disc(uri="/track.mp3", metadata=DiscMetadata(), option=DiscOption())
    console, buf = console_capture
    display_disc("tag-1", disc, console=console)
    output = buf.getvalue()

    assert "tag-1" in output
    assert "Artist   : /" in output
    assert "Album    : /" in output
    assert "Track    : /" in output
    assert "Playlist : /" in output


def test_display_library_table_shows_type_and_title_after_id(sample_discs, console_capture):
    console, buf = console_capture
    display_library_table(sample_discs, console=console)
    header = next(line for line in buf.getvalue().splitlines() if "URI" in line)

    assert header.index("ID") < header.index("Type") < header.index("Title") < header.index("URI")


def test_display_library_table_never_truncates_the_id_on_narrow_terminals(sample_discs):
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, no_color=True, width=80)
    display_library_table(sample_discs, console=console)
    output = buf.getvalue()

    assert "abc123" in output
    assert "xyz789" in output
    assert all(cell_len(line) <= 80 for line in output.splitlines())


def render_table(discs: dict[str, Disc], width: int) -> list[str]:
    buf = StringIO()
    display_library_table(discs, console=Console(file=buf, force_terminal=False, no_color=True, width=width))
    return buf.getvalue().splitlines()


@pytest.fixture
def nfc_discs() -> dict[str, Disc]:
    return {
        "04:A3:2B:1C:9F:80:00": Disc(
            uri="spotify:album:3IvUwbVgAZSqNh06PVxwG7", metadata=DiscMetadata(artist="Zubi", album="Dear Z")
        ),
        "04:7E:91:2A:C4:5D:80": Disc(
            uri="spotify:playlist:37i9dQZF1DXcBWIGoYBM5M", metadata=DiscMetadata(playlist="Today's Top Hits")
        ),
    }


def test_display_library_table_keeps_type_and_title_readable_with_nfc_uids_at_80_columns(nfc_discs):
    lines = render_table(nfc_discs, width=80)
    output = "\n".join(lines)

    assert all(cell_len(line) <= 80 for line in lines)
    assert "04:A3:2B:1C:9F:80:00" in output
    assert "04:7E:91:2A:C4:5D:80" in output
    assert "💿 Album" in output
    assert "🎧 Playlist" in output
    assert "Zubi — Dear Z" in output
    assert "Today's Top Hits" in output


def test_display_library_table_drops_raw_columns_before_type_and_title(nfc_discs):
    header = next(line for line in render_table(nfc_discs, width=80) if "Title" in line)

    assert "Type" in header
    assert "Playlist" not in header
    assert "Track" not in header


def test_display_library_table_shows_every_column_on_wide_terminals(sample_discs):
    header = next(line for line in render_table(sample_discs, width=200) if "Title" in line)

    for label in ("ID", "Type", "Title", "URI", "Artist", "Album", "Track", "Playlist", "Shuffle"):
        assert label in header


def test_display_library_table_fits_with_a_very_long_id():
    long_id = "x" * 50
    lines = render_table({long_id: Disc(uri="/a.mp3", metadata=DiscMetadata(artist="Zubi", album="Dear Z"))}, 80)

    assert all(cell_len(line) <= 80 for line in lines)
    assert long_id in "\n".join(lines)


def test_display_library_table_measures_the_id_in_terminal_cells(nfc_discs):
    wide_id = "タグ一二三四五六七八"  # 10 characters, 20 cells
    discs = {wide_id: nfc_discs["04:A3:2B:1C:9F:80:00"]}
    lines = render_table(discs, 80)

    assert all(cell_len(line) <= 80 for line in lines)
    assert wide_id in "\n".join(lines)


def test_every_disc_field_is_either_kept_or_droppable_in_the_table():
    assert set(TABLE_DROP_ORDER) | {"Type", "Title"} == {label for label, _ in DISC_FIELDS}


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (DiscMetadata(), 'Delete disc "tag-123"?'),
        (DiscMetadata(artist="Zubi", track="dey ok"), 'Delete disc "tag-123" (Zubi — dey ok)?'),
    ],
)
def test_build_remove_confirmation(metadata, expected):
    disc = Disc(uri="/music/song.mp3", metadata=metadata)

    assert build_remove_confirmation("tag-123", disc) == expected
