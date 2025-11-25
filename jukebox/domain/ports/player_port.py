from abc import ABC, abstractmethod


class PlayerPort(ABC):
    """Port for music player implementations."""

    @abstractmethod
    def play(self, uri: str, shuffle: bool = False) -> None:
        """Start playing a URI with optional shuffle."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""
        pass

    @abstractmethod
    def resume(self) -> None:
        """Resume playback."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop playback."""
        pass
