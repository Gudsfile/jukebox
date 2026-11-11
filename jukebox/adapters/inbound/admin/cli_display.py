from collections.abc import Callable

from rich.console import Console
from rich.table import Table

from jukebox.domain.entities import Disc

MAX_COL_WIDTH = 20

DISC_FIELDS: list[tuple[str, Callable[[Disc], str]]] = [
    ("Type", lambda disc: disc.metadata.display_type),
    ("Title", lambda disc: disc.metadata.display_title),
    ("URI", lambda disc: disc.uri),
    ("Artist", lambda disc: disc.metadata.artist or "/"),
    ("Album", lambda disc: disc.metadata.album or "/"),
    ("Track", lambda disc: disc.metadata.track or "/"),
    ("Playlist", lambda disc: disc.metadata.playlist or "/"),
    ("Shuffle", lambda disc: str(disc.option.shuffle)),
]
LABEL_WIDTH = max(len(label) for label, _ in DISC_FIELDS)


def _disc_lines(disc: Disc) -> list[str]:
    return [f"  {label:<{LABEL_WIDTH}} : {value(disc)}" for label, value in DISC_FIELDS]


def display_disc(tag_id: str, disc: Disc, console: Console | None = None) -> None:
    _console = console or Console()
    _console.print(f"\n📀 Disc: {tag_id}")
    for line in _disc_lines(disc):
        _console.print(line)


def display_library_line(discs: dict[str, Disc]) -> None:
    if not discs:
        print("The library is empty")
        return

    print("=== Discs Library ===\n")
    for disc_id, disc in discs.items():
        print(f"ID : {disc_id}")
        for line in _disc_lines(disc):
            print(line)
        print("-" * 30)


def display_library_table(discs: dict[str, Disc], console: Console | None = None) -> None:
    _console = console or Console()
    if not discs:
        _console.print("The library is empty")
        return

    table = Table(title="Discs Library")
    table.add_column("ID", no_wrap=True, max_width=MAX_COL_WIDTH)
    for label, _ in DISC_FIELDS:
        table.add_column(label, no_wrap=True, max_width=MAX_COL_WIDTH)

    for disc_id, disc in discs.items():
        table.add_row(str(disc_id), *(value(disc) for _, value in DISC_FIELDS))

    _console.print(table)
