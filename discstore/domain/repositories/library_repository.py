from abc import ABC, abstractmethod

from discstore.domain.entities.library import Library


class LibraryRepository(ABC):
    @abstractmethod
    def load(self) -> Library:
        pass

    @abstractmethod
    def save(self, library: Library) -> None:
        pass
