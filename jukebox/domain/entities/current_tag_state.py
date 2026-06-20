from dataclasses import dataclass
from typing import Literal

CurrentTagCommand = Literal["set", "clear"]

CURRENT_TAG_ABSENCE_GRACE_SECONDS: float = 1.0


@dataclass(frozen=True)
class NoTag:
    last_event_timestamp: float | None = None


@dataclass(frozen=True)
class TagPresent:
    tag: str
    last_event_timestamp: float | None = None


@dataclass(frozen=True)
class TagRemoved:
    tag: str
    removed_at: float
    last_event_timestamp: float | None = None


CurrentTagState = NoTag | TagPresent | TagRemoved


@dataclass(frozen=True)
class CurrentTagContext:
    grace_seconds: float
