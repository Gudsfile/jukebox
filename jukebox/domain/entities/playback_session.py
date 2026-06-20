from typing import Self

from pydantic import BaseModel, model_validator

from .playback_action import PlaybackAction


class PlaybackCommandRetry(BaseModel):
    """Tracks retry timing for a failed playback command."""

    action: PlaybackAction
    tag_id: str | None = None
    first_failed_at: float
    last_failed_at: float
    attempt_count: int
    next_retry_at: float | None
    exhausted: bool = False

    @model_validator(mode="after")
    def validate_tag_id_matches_action(self) -> Self:
        if self.action == PlaybackAction.PLAY:
            if self.tag_id is None:
                raise ValueError("tag_id is required for PLAY retry")
        elif self.tag_id is not None:
            raise ValueError("tag_id is only valid for PLAY retry")
        return self

    def matches(self, *, action: PlaybackAction, tag_id: str | None = None) -> bool:
        return self.action == action and self.tag_id == tag_id


class PlaybackSession(BaseModel):
    """Tracks the logical playback state."""

    playing_tag: str | None = None
    paused_at: float | None = None
    playing_tag_removed_at: float | None = None
    playback_command_retry: PlaybackCommandRetry | None = None
