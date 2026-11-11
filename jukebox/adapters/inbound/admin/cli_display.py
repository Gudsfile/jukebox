from collections.abc import Callable

from rich.cells import cell_len
from rich.console import Console
from rich.table import Table

from jukebox.domain.entities import Disc

MAX_COL_WIDTH = 20

# A new field also needs a place in TABLE_DROP_ORDER (and maybe TABLE_COL_BOUNDS) below
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

# Table only: Type and Title get a guaranteed width, and Title may grow past MAX_COL_WIDTH.
# The raw fields (redundant with Title) shrink first, then disappear in TABLE_DROP_ORDER.
TABLE_COL_BOUNDS: dict[str, tuple[int, int]] = {"Type": (11, 11), "Title": (24, 40), "Shuffle": (5, 7)}
RAW_COL_BOUNDS = (8, MAX_COL_WIDTH)
TABLE_DROP_ORDER = ["Playlist", "Track", "Album", "Artist", "Shuffle", "URI"]
COL_CHROME = 3  # left border + padding on both sides


def _disc_lines(disc: Disc) -> list[str]:
    return [f"  {label:<{LABEL_WIDTH}} : {value(disc)}" for label, value in DISC_FIELDS]


def display_disc(tag_id: str, disc: Disc, console: Console | None = None) -> None:
    _console = console or Console()
    _console.print(f"\n📀 Disc: {tag_id}")
    for line in _disc_lines(disc):
        _console.print(line)


def build_remove_confirmation(tag_id: str, disc: Disc) -> str:
    suffix = f" ({disc.metadata.display_title})" if disc.metadata.has_title else ""
    return f'Delete disc "{tag_id}"{suffix}?'


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

    # The ID is what users copy into `library get`, so it never shrinks
    id_width = max(cell_len(str(disc_id)) for disc_id in discs)
    widths = _table_widths(discs, available=_console.width - 1 - (id_width + COL_CHROME))
    fields = [(label, value) for label, value in DISC_FIELDS if label in widths]

    table = Table(title="Discs Library")
    table.add_column("ID", no_wrap=True, min_width=id_width)
    for label, _ in fields:
        table.add_column(label, no_wrap=True, width=widths[label])

    for disc_id, disc in discs.items():
        table.add_row(str(disc_id), *(value(disc) for _, value in fields))

    _console.print(table)


def _table_widths(discs: dict[str, Disc], available: int) -> dict[str, int]:
    """Width of each shown column, in DISC_FIELDS order, which is also the order they grow in."""
    targets: dict[str, int] = {}
    minimums: dict[str, int] = {}
    for label, value in DISC_FIELDS:
        low, high = TABLE_COL_BOUNDS.get(label, RAW_COL_BOUNDS)
        natural = max(cell_len(label), *(cell_len(value(disc)) for disc in discs.values()))
        targets[label] = min(natural, high)
        minimums[label] = min(targets[label], low)

    shown = [label for label, _ in DISC_FIELDS]
    for label in TABLE_DROP_ORDER:
        if sum(minimums[col] + COL_CHROME for col in shown) <= available:
            break
        shown.remove(label)

    spare = available - sum(minimums[col] + COL_CHROME for col in shown)
    widths = {}
    for label in shown:
        extra = min(max(spare, 0), targets[label] - minimums[label])
        widths[label] = minimums[label] + extra
        spare -= extra
    # Only Type and Title are left and still too wide (very long ID): give up their minimums
    for label in reversed(shown):
        if spare >= 0:
            break
        cut = min(-spare, widths[label] - 1)
        widths[label] -= cut
        spare += cut
    return widths
