from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class ListDiscs:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self) -> dict[str, Disc]:
        return self.repository.list_discs()
