from typing import Optional

from discstore.domain.entities import CurrentDisc
from discstore.domain.repositories import CurrentDiscRepository


class GetCurrentDisc:
    def __init__(self, repository: CurrentDiscRepository):
        self.repository = repository

    def execute(self) -> Optional[CurrentDisc]:
        return self.repository.get()
