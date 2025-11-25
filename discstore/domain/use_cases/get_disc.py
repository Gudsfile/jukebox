from discstore.domain.entities.disc import Disc
from discstore.domain.repositories.library_repository import LibraryRepository


class GetDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str) -> Disc:
        library = self.repository.load()

        if tag_id not in library.discs:
            raise ValueError(f"Tag not found: tag_id='{tag_id}'")

        return library.discs[tag_id]
