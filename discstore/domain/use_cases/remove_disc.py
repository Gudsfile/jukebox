from discstore.domain.repositories import LibraryRepository


class RemoveDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, tag_id: str) -> None:
        library = self.repository.load()

        if tag_id not in library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        library.discs.pop(tag_id)
        self.repository.save(library)
