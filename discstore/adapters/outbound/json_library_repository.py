import json
import logging

from pydantic import ValidationError

from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository

LOGGER = logging.getLogger("discstore")


class JsonLibraryRepository(LibraryRepository):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> Library:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Library.model_validate(data)
        except FileNotFoundError as err:
            LOGGER.warning(f"File not found, continuing with an empty library: filepath: {self.filepath}", err)
            return Library()
        except (json.JSONDecodeError, ValidationError) as err:
            LOGGER.warning(
                f"Error deserializing library, continuing with empty library: filepath: {self.filepath}", err
            )
            return Library()

    def save(self, library: Library) -> None:
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(library.model_dump(), f, indent=2, ensure_ascii=False)
