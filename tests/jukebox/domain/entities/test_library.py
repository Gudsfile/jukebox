import json
from pathlib import Path

from jukebox.domain.entities import Disc, DiscMetadata, Library

LIBRARY_EXAMPLE_PATH = Path(__file__).parents[4] / "library.example.json"


def test_library():
    discs = {"tag:123": Disc(uri="uri:123", metadata=DiscMetadata())}
    library = Library(discs=discs)
    assert library.discs == discs


def test_library_example_is_valid():
    """library.example.json should load without validation errors"""
    data = json.loads(LIBRARY_EXAMPLE_PATH.read_text(encoding="utf-8"))
    library = Library.model_validate(data)
    assert len(library.discs) == 3
