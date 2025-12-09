import json
import logging
from typing import Optional

from pydantic import ValidationError

from jukebox.domain.entities import Disc, Library
from jukebox.domain.repositories import LibraryRepository

LOGGER = logging.getLogger("jukebox")


class JsonLibraryAdapter(LibraryRepository):
    """JSON file-based implementation of LibraryRepository."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> Library:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Library.model_validate(data)
        except FileNotFoundError as err:
            LOGGER.warning(f"File not found, continuing with an empty library: filepath: {self.filepath}, error: {err}")
            return Library()
        except (json.JSONDecodeError, ValidationError) as err:
            LOGGER.warning(
                f"Error deserializing library, continuing with empty library: filepath: {self.filepath}, error: {err}"
            )
            return Library()

    def save(self, library: Library) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(library.model_dump(), f, indent=2, ensure_ascii=False)

    def get_disc(self, tag_id: str) -> Optional[Disc]:
        library = self.load()
        return library.discs.get(tag_id)
