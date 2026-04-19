from abc import ABC, abstractmethod


class ReaderPort(ABC):
    """Port for tag reader implementations."""

    @abstractmethod
    def read(self) -> str | None:
        """Read a tag ID. Returns None if no tag detected."""
        pass
