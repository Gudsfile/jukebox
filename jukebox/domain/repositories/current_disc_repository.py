from abc import ABC, abstractmethod
from typing import Optional

from jukebox.domain.entities import CurrentDisc


class CurrentDiscRepository(ABC):
    @abstractmethod
    def get(self) -> Optional[CurrentDisc]:
        pass

    @abstractmethod
    def save(self, current_disc: CurrentDisc) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def clear_if_matches(self, tag_id: str) -> bool:
        pass
