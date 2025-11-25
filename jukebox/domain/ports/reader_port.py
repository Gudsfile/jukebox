from abc import ABC, abstractmethod
from typing import Optional


class ReaderPort(ABC):
    """Port for tag reader implementations."""

    @abstractmethod
    def read(self) -> Optional[str]:
        """Read a tag ID. Returns None if no tag detected."""
        pass
