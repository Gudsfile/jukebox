from rich.console import Console
from rich.table import Table

from jukebox.domain.entities import Disc


def display_disc(tag_id: str, disc: Disc) -> None:
    print(f"\n📀 Disc: {tag_id}")
    print(f"  URI      : {disc.uri}")
    print(f"  Artist   : {disc.metadata.artist or '/'}")
    print(f"  Album    : {disc.metadata.album or '/'}")
    print(f"  Track    : {disc.metadata.track or '/'}")
    print(f"  Playlist : {disc.metadata.playlist or '/'}")
    print(f"  Shuffle  : {disc.option.shuffle}")


def display_library_line(discs: dict[str, Disc]) -> None:
    if not discs:
        print("The library is empty")
        return

    print("=== Discs Library ===\n")
    for disc_id, disc in discs.items():
        print(f"ID : {disc_id}")
        print(f"  URI      : {disc.uri}")
        print(f"  Artist   : {disc.metadata.artist or '/'}")
        print(f"  Album    : {disc.metadata.album or '/'}")
        print(f"  Track    : {disc.metadata.track or '/'}")
        print(f"  Playlist : {disc.metadata.playlist or '/'}")
        print(f"  Shuffle  : {disc.option.shuffle}")
        print("-" * 30)


def display_library_table(discs: dict[str, Disc]) -> None:
    if not discs:
        print("The library is empty")
        return

    table = Table(title="Discs Library")
    table.add_column("ID", no_wrap=True, max_width=20)
    table.add_column("URI", no_wrap=True, max_width=20)
    table.add_column("Artist", no_wrap=True, max_width=20)
    table.add_column("Album", no_wrap=True, max_width=20)
    table.add_column("Track", no_wrap=True, max_width=20)
    table.add_column("Playlist", no_wrap=True, max_width=20)
    table.add_column("Shuffle")

    for disc_id, disc in discs.items():
        table.add_row(
            str(disc_id),
            disc.uri,
            disc.metadata.artist or "/",
            disc.metadata.album or "/",
            disc.metadata.track or "/",
            disc.metadata.playlist or "/",
            str(disc.option.shuffle),
        )

    Console().print(table)
