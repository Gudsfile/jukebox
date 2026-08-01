from abc import ABC, abstractmethod


class PlayerPort(ABC):
    """Port for music player implementations."""

    @abstractmethod
    def play(self, uri: str, shuffle: bool = False) -> None:
        """Start playing a URI with optional shuffle."""

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""

    @abstractmethod
    def resume(self) -> None:
        """Resume playback."""

    @abstractmethod
    def stop(self) -> None:
        """Stop playback."""
