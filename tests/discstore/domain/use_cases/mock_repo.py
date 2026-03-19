from discstore.domain.entities import Disc, Library
from discstore.domain.repositories import LibraryRepository


class MockRepo(LibraryRepository):
    def __init__(self, library: Library):
        self.library = library.model_copy(deep=True)
        self.add_calls: list[tuple[str, Disc]] = []
        self.update_calls: list[tuple[str, Disc]] = []
        self.remove_calls: list[str] = []
        self.get_calls: list[str] = []
        self.list_calls = 0

    @staticmethod
    def _copy_disc(disc: Disc) -> Disc:
        return disc.model_copy(deep=True)

    def list_discs(self):
        self.list_calls += 1
        return {tag_id: self._copy_disc(disc) for tag_id, disc in self.library.discs.items()}

    def get_disc(self, tag_id: str):
        self.get_calls.append(tag_id)
        disc = self.library.discs.get(tag_id)
        if disc is None:
            return None

        return self._copy_disc(disc)

    def add_disc(self, tag_id: str, disc: Disc):
        self.add_calls.append((tag_id, self._copy_disc(disc)))
        if tag_id in self.library.discs:
            raise ValueError(f"Already existing tag: tag_id='{tag_id}'")

        self.library.discs[tag_id] = self._copy_disc(disc)

    def update_disc(self, tag_id: str, disc: Disc):
        self.update_calls.append((tag_id, self._copy_disc(disc)))
        if tag_id not in self.library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        self.library.discs[tag_id] = self._copy_disc(disc)

    def remove_disc(self, tag_id: str):
        self.remove_calls.append(tag_id)
        if tag_id not in self.library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        self.library.discs.pop(tag_id)
