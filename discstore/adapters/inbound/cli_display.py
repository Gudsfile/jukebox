# adapters/inbound/cli_display.py

from typing import Dict

from discstore.domain.entities.disc import Disc

MAX_COL_WIDTH = 20


def display_library_line(discs: Dict[str, Disc]) -> None:
    if not discs:
        print("La librairie est vide")
        return

    print("=== Librairie de CDs ===\n")
    for disc_id, disc in discs.items():
        print(f"ID : {disc_id}")
        print(f"  URI      : {disc.uri}")
        print(f"  Artiste  : {disc.metadata.artist or '/'}")
        print(f"  Album    : {disc.metadata.album or '/'}")
        print(f"  Titre    : {disc.metadata.track or '/'}")
        print(f"  Playlist : {disc.metadata.playlist or '/'}")
        print(f"  Test     : {disc.option.is_test}")
        print(f"  Shuffle  : {disc.option.shuffle}")
        print("-" * 30)


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def display_library_table(discs: Dict[str, Disc]) -> None:
    if not discs:
        print("La librairie est vide")
        return

    headers = ["ID", "URI", "Artiste", "Album", "Titre", "Playlist", "Test", "Shuffle"]
    rows = []
    for disc_id, disc in discs.items():
        rows.append(
            [
                truncate(str(disc_id), MAX_COL_WIDTH),
                truncate(disc.uri, MAX_COL_WIDTH),
                truncate(disc.metadata.artist or "/", MAX_COL_WIDTH),
                truncate(disc.metadata.album or "/", MAX_COL_WIDTH),
                truncate(disc.metadata.track or "/", MAX_COL_WIDTH),
                truncate(disc.metadata.playlist or "/", MAX_COL_WIDTH),
                str(disc.option.is_test),
                str(disc.option.shuffle),
            ]
        )

    cols = list(zip(*([headers] + rows)))
    col_widths = [max(len(str(item)) for item in col) for col in cols]

    def format_line(line):
        return " | ".join(f"{str(item):<{col_widths[i]}}" for i, item in enumerate(line))

    print(format_line(headers))
    print("-+-".join("-" * w for w in col_widths))
    for row in rows:
        print(format_line(row))
