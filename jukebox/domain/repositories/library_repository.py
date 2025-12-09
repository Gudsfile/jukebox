from abc import ABC, abstractmethod
from typing import Optional

from jukebox.domain.entities import Disc, Library


class LibraryRepository(ABC):
    @abstractmethod
    def load(self) -> Library:
        pass

    @abstractmethod
    def save(self, library: Library) -> None:
        pass

    @abstractmethod
    def get_disc(self, tag_id: str) -> Optional[Disc]:
        pass
