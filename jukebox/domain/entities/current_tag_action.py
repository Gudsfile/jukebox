from enum import Enum


class CurrentTagAction(str, Enum):
    """Actions that can be taken on the physical current tag state."""

    SET = "set"
    CLEAR = "clear"
    KEEP = "keep"
    REMOVE = "remove"
    RESTORE = "restore"
