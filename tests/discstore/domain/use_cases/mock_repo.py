from typing import Optional

from discstore.domain.entities import Library
from discstore.domain.repositories import LibraryRepository


class MockRepo(LibraryRepository):
    def __init__(self, library: Library):
        self.saved_library: Optional[Library] = None
        self.library = library

    def load(self):
        return self.library

    def save(self, library: Library):
        self.saved_library = library

    def get_disc(self, tag: str):
        return self.library.discs.get(tag)
