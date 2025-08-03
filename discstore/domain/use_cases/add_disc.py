from discstore.domain.entities.disc import Disc
from discstore.domain.repositories.library_repository import LibraryRepository


class AddDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, disc_id: str, disc: Disc) -> None:
        library = self.repository.load()

        if disc_id in library.discs:
            raise ValueError(f"Un disque avec l'ID '{disc_id}' existe déjà.")

        library.discs[disc_id] = disc
        self.repository.save(library)
