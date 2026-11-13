class PlaybackError(Exception):
    """Raised when a player operation fails."""


class NothingToResumeError(PlaybackError):
    """Raised when resume is impossible because the player no longer holds what was played (e.g. its queue was cleared or replaced)."""
