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

    @abstractmethod
    def snapshot(self) -> bytes | None:
        """Return the stored library as is, even if unreadable, or None when there is none."""

    @abstractmethod
    def restore(self, snapshot: bytes | None) -> None:
        """Put back the stored library as returned by snapshot()."""
