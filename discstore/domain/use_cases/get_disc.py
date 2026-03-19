from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class GetDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str) -> Disc:
        disc = self.repository.get_disc(tag_id)
        if disc is None:
            raise ValueError(f"Tag not found: tag_id='{tag_id}'")

        return disc
