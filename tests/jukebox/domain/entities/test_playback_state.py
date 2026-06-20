import dataclasses

import pytest

from jukebox.domain.entities import Idle, Paused, PlaybackCommand, Playing, RetryState, Waiting


def _retry(action: PlaybackCommand = "play", tag_id: str | None = "tag-1") -> RetryState:
    return RetryState(
        action=action,
        tag_id=tag_id,
        first_failed_at=100.0,
        last_failed_at=100.0,
        attempt_count=1,
        next_retry_at=100.1,
    )


@pytest.mark.parametrize(
    "state",
    [
        Idle(),
        Playing(tag="tag-1"),
        Waiting(tag="tag-1", removed_at=100.0),
        Paused(tag="tag-1", paused_at=100.0),
    ],
)
def test_states_are_frozen(state):
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.retry = None


def test_retry_state_matches_action_and_tag():
    retry = _retry(action="play", tag_id="tag-1")
    assert retry.matches(action="play", tag_id="tag-1")
    assert not retry.matches(action="play", tag_id="tag-2")
    assert not retry.matches(action="pause")


def test_retry_state_matches_none_tag_for_non_play_actions():
    retry = _retry(action="pause", tag_id=None)
    assert retry.matches(action="pause")
    assert retry.matches(action="pause", tag_id=None)
    assert not retry.matches(action="resume")


def test_retry_state_play_requires_tag_id():
    with pytest.raises(ValueError, match="requires tag_id"):
        RetryState(
            action="play",
            tag_id=None,
            first_failed_at=100.0,
            last_failed_at=100.0,
            attempt_count=1,
            next_retry_at=100.1,
        )


def test_retry_state_non_play_forbids_tag_id():
    with pytest.raises(ValueError, match="must not have tag_id"):
        RetryState(
            action="pause",
            tag_id="tag-1",
            first_failed_at=100.0,
            last_failed_at=100.0,
            attempt_count=1,
            next_retry_at=100.1,
        )
