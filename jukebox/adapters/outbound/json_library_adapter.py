from typing import Union

from discstore.adapters.outbound.json_library_repository import JsonLibraryRepository
from discstore.domain.entities.disc import Disc
from jukebox.domain.ports import LibraryPort


class JsonLibraryAdapter(LibraryPort):
    """Adapter for JSON library implementing LibraryPort."""

    def __init__(self, library_path: str):
        self.repository = JsonLibraryRepository(library_path)

    def get_disc(self, tag_id: str) -> Union[Disc, None]:
        library = self.repository.load()
        return library.discs.get(tag_id)
