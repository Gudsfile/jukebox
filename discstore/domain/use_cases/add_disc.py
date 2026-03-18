from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class AddDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str, disc: Disc) -> None:
        self.repository.add_disc(tag_id, disc)
