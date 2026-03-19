from discstore.domain.repositories import LibraryRepository


class RemoveDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str) -> None:
        self.repository.remove_disc(tag_id)
