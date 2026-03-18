from typing import Dict

from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class SearchDiscs:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, query: str) -> Dict[str, Disc]:
        return self.repository.search_discs(query)
