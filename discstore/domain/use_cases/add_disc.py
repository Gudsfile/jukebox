from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class AddDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str, disc: Disc) -> None:
        library = self.repository.load()

        if tag_id in library.discs:
            raise ValueError(f"Already existing tag: tag_id='{tag_id}'")

        library.discs[tag_id] = disc
        self.repository.save(library)
