from abc import ABC, abstractmethod
from typing import Optional

from jukebox.domain.entities import Disc, DiscMetadata, DiscOption


class LibraryRepository(ABC):
    @abstractmethod
    def list_discs(self) -> dict[str, Disc]:
        pass

    @abstractmethod
    def get_disc(self, tag_id: str) -> Optional[Disc]:
        pass

    @abstractmethod
    def add_disc(self, tag_id: str, disc: Disc) -> None:
        pass

    @abstractmethod
    def edit_disc(
        self,
        tag_id: str,
        uri: Optional[str] = None,
        metadata: Optional[DiscMetadata] = None,
        option: Optional[DiscOption] = None,
    ) -> None:
        pass

    @abstractmethod
    def remove_disc(self, tag_id: str) -> None:
        pass

    @abstractmethod
    def search_discs(self, query: str) -> dict[str, Disc]:
        pass
