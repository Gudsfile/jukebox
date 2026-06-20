from dataclasses import dataclass
from typing import Literal

PlaybackCommand = Literal["play", "pause", "resume", "stop"]

PLAYBACK_RETRY_DELAYS_SECONDS: tuple[float, ...] = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)


@dataclass(frozen=True)
class RetryState:
    """Tracks retry timing for a failed playback command."""

    action: PlaybackCommand
    tag_id: str | None
    first_failed_at: float
    last_failed_at: float
    attempt_count: int
    next_retry_at: float | None
    exhausted: bool = False

    def __post_init__(self) -> None:
        if self.action == "play" and self.tag_id is None:
            raise ValueError("RetryState action='play' requires tag_id")
        if self.action != "play" and self.tag_id is not None:
            raise ValueError(f"RetryState action='{self.action}' must not have tag_id")

    def matches(self, *, action: PlaybackCommand, tag_id: str | None = None) -> bool:
        return self.action == action and self.tag_id == tag_id


@dataclass(frozen=True)
class Idle:
    retry: RetryState | None = None


@dataclass(frozen=True)
class Playing:
    tag: str
    retry: RetryState | None = None


@dataclass(frozen=True)
class Waiting:
    tag: str
    removed_at: float
    retry: RetryState | None = None


@dataclass(frozen=True)
class Paused:
    tag: str
    paused_at: float
    retry: RetryState | None = None


PlaybackState = Idle | Playing | Waiting | Paused


@dataclass(frozen=True)
class TransitionContext:
    """Configuration bundle for the playback state transition function."""

    pause_delay: float
    max_pause_duration: float
    retry_delays: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.retry_delays:
            raise ValueError("retry_delays must not be empty")
