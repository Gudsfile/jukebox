from typing import Optional

from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository


class MockRepo(LibraryRepository):
    def __init__(self, library: Library):
        self.saved_library: Optional[Library] = None
        self.library = library

    def load(self):
        return self.library

    def save(self, library: Library):
        self.saved_library = library
