from abc import ABC, abstractmethod

from jukebox.domain.entities import Disc, Library


class LibraryRepository(ABC):
    @abstractmethod
    def list_discs(self) -> dict[str, Disc]:
        pass

    @abstractmethod
    def get_disc(self, tag_id: str) -> Disc | None:
        pass

    @abstractmethod
    def add_disc(self, tag_id: str, disc: Disc) -> None:
        pass

    @abstractmethod
    def update_disc(self, tag_id: str, disc: Disc) -> None:
        pass

    @abstractmethod
    def remove_disc(self, tag_id: str) -> None:
        pass

    @abstractmethod
    def replace_library(self, library: Library) -> None:
        pass
