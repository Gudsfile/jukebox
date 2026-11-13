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
        """Resume what the last play() started.

        Raises NothingToResumeError if the player no longer holds it (e.g. its queue was cleared,
        or replaced from another app).
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop playback."""
