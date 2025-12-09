from typing import Dict

from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class ListDiscs:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self) -> Dict[str, Disc]:
        return self.repository.load().discs
