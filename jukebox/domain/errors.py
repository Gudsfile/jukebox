class PlaybackError(Exception):
    """Raised when a player operation fails."""


class NothingToResumeError(PlaybackError):
    """Raised when resume is impossible because the player has nothing to resume (e.g. its queue was cleared)."""
