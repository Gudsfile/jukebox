from abc import ABC, abstractmethod


class CurrentTagRepository(ABC):
    @abstractmethod
    def get(self) -> str | None:
        pass

    @abstractmethod
    def set(self, tag_id: str) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
