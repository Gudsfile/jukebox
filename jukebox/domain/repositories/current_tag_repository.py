from abc import ABC, abstractmethod
from typing import Optional


class CurrentTagRepository(ABC):
    @abstractmethod
    def get(self) -> Optional[str]:
        pass

    @abstractmethod
    def set(self, tag_id: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
