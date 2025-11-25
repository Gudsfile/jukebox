from abc import ABC, abstractmethod
from typing import Optional

from discstore.domain.entities.disc import Disc


class LibraryPort(ABC):
    """Port for library implementations."""

    @abstractmethod
    def get_disc(self, tag_id: str) -> Optional[Disc]:
        """Get disc by tag ID. Returns None if not found."""
        pass
