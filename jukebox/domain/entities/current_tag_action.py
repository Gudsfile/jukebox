from enum import StrEnum


class CurrentTagAction(StrEnum):
    """Actions that can be taken on the physical current tag state."""

    SET = "set"
    CLEAR = "clear"
    KEEP = "keep"
    REMOVE = "remove"
    RESTORE = "restore"
