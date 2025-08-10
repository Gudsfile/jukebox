from discstore.domain.entities.disc import Disc
from discstore.domain.repositories.library_repository import LibraryRepository


class EditDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str, disc: Disc) -> None:
        library = self.repository.load()

        if tag_id not in library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        library.discs[tag_id] = disc
        self.repository.save(library)
