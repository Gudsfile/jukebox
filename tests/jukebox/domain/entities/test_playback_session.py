import pytest
from pydantic import ValidationError

from jukebox.domain.entities import PlaybackAction, PlaybackCommandRetry


def make_retry(action: PlaybackAction, tag_id: str | None = None) -> PlaybackCommandRetry:
    return PlaybackCommandRetry(
        action=action,
        tag_id=tag_id,
        first_failed_at=100.0,
        last_failed_at=100.0,
        attempt_count=1,
        next_retry_at=100.1,
    )


def test_playback_command_retry_requires_tag_id_for_play():
    with pytest.raises(ValidationError, match="tag_id is required for PLAY retry"):
        make_retry(PlaybackAction.PLAY)


def test_playback_command_retry_rejects_tag_id_for_non_play():
    with pytest.raises(ValidationError, match="tag_id is only valid for PLAY retry"):
        make_retry(PlaybackAction.PAUSE, tag_id="test-tag")


def test_playback_command_retry_matches_action_and_tag_id():
    retry = make_retry(PlaybackAction.PLAY, tag_id="test-tag")

    assert retry.matches(action=PlaybackAction.PLAY, tag_id="test-tag") is True
    assert retry.matches(action=PlaybackAction.PLAY, tag_id="other-tag") is False
    assert retry.matches(action=PlaybackAction.PAUSE, tag_id="test-tag") is False
