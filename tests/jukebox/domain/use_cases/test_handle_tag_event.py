from unittest.mock import MagicMock

import pytest

from jukebox.domain.entities import (
    PLAYBACK_RETRY_DELAYS_SECONDS,
    Disc,
    DiscMetadata,
    DiscOption,
    Idle,
    Paused,
    Playing,
    TagEvent,
    TransitionContext,
    Waiting,
)
from jukebox.domain.errors import PlaybackError
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent


@pytest.fixture
def mock_player():
    return MagicMock()


@pytest.fixture
def mock_library():
    library = MagicMock()
    library.get_disc.return_value = Disc(
        uri="uri:123",
        metadata=DiscMetadata(artist="Test Artist", album="Test Album", track="Test Track"),
        option=DiscOption(shuffle=False),
    )
    return library


@pytest.fixture
def ctx():
    return TransitionContext(
        pause_delay=3,
        max_pause_duration=50,
        retry_delays=PLAYBACK_RETRY_DELAYS_SECONDS,
    )


@pytest.fixture
def handle_tag_event(mock_player, mock_library, ctx):
    return HandleTagEvent(player=mock_player, library=mock_library, ctx=ctx)


# ---------------------------------------------------------------------------
# PLAY
# ---------------------------------------------------------------------------


def test_handle_play_action_with_existing_disc(handle_tag_event, mock_player, mock_library):
    state = Idle()
    tag_event = TagEvent(tag_id="test-tag", timestamp=100.0)

    new_state = handle_tag_event.execute(tag_event, state)

    mock_library.get_disc.assert_called_once_with("test-tag")
    mock_player.play.assert_called_once_with("uri:123", False)
    assert isinstance(new_state, Playing)
    assert new_state.tag == "test-tag"
    assert new_state.retry is None


def test_handle_play_action_with_shuffle(handle_tag_event, mock_player, mock_library):
    mock_library.get_disc.return_value = Disc(uri="uri:456", metadata=DiscMetadata(), option=DiscOption(shuffle=True))
    new_state = handle_tag_event.execute(TagEvent(tag_id="shuffle-tag", timestamp=100.0), Idle())
    mock_player.play.assert_called_once_with("uri:456", True)
    assert isinstance(new_state, Playing)


def test_handle_play_action_with_nonexistent_disc(handle_tag_event, mock_player, mock_library):
    mock_library.get_disc.return_value = None
    handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.0), Idle())
    mock_player.play.assert_not_called()


def test_tag_without_disc_plays_when_disc_becomes_available(handle_tag_event, mock_player, mock_library):
    """Should play on second read when disc wasn't in library on first read."""
    promoted_disc = Disc(uri="uri:promoted", metadata=DiscMetadata(), option=DiscOption(shuffle=True))
    mock_library.get_disc.side_effect = [None, promoted_disc]

    state = handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.0), Idle())
    mock_player.play.assert_not_called()

    handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.2), state)
    mock_player.play.assert_called_once_with("uri:promoted", True)


# ---------------------------------------------------------------------------
# RESUME
# ---------------------------------------------------------------------------


def test_handle_resume_action(handle_tag_event, mock_player):
    state = Paused(tag="test-tag", paused_at=90.0)
    new_state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), state)

    mock_player.resume.assert_called_once()
    assert isinstance(new_state, Playing)
    assert new_state.tag == "test-tag"
    assert new_state.retry is None


def test_same_tag_after_expired_pause_restarts_play(handle_tag_event, mock_player):
    """Same tag tapped after max_pause_duration (before STOP fires) -> PLAY restart, not RESUME.

    This narrow window exists because STOP only fires on a no-tag tick.
    If the user taps the same card before the next no-tag tick fires STOP,
    the pause is already expired so RESUME is not issued: PLAY restarts instead.
    """
    # paused_at=40.0, timestamp=100.0 -> 60s > 50s max_pause_duration
    state = Paused(tag="test-tag", paused_at=40.0)
    new_state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), state)

    mock_player.play.assert_called_once()
    mock_player.resume.assert_not_called()
    assert isinstance(new_state, Playing)
    assert new_state.tag == "test-tag"


# ---------------------------------------------------------------------------
# PAUSE
# ---------------------------------------------------------------------------


def test_handle_pause_action(handle_tag_event, mock_player):
    state = Waiting(tag="test-tag", removed_at=5.0)
    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.2), state)

    mock_player.pause.assert_called_once()
    assert isinstance(new_state, Paused)
    assert new_state.paused_at == pytest.approx(100.2)


def test_handle_pause_then_stop_after_max_pause_duration(mock_player, mock_library):
    ctx = TransitionContext(
        pause_delay=0.25,
        max_pause_duration=0.5,
        retry_delays=PLAYBACK_RETRY_DELAYS_SECONDS,
    )
    hte = HandleTagEvent(player=mock_player, library=mock_library, ctx=ctx)

    state = Waiting(tag="test-tag", removed_at=99.76)

    state = hte.execute(TagEvent(tag_id=None, timestamp=100.02), state)
    assert isinstance(state, Paused)
    assert state.paused_at == pytest.approx(100.02)
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    state = hte.execute(TagEvent(tag_id=None, timestamp=100.32), state)
    assert isinstance(state, Paused)
    assert state.paused_at == pytest.approx(100.02)
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    state = hte.execute(TagEvent(tag_id=None, timestamp=100.62), state)
    mock_player.stop.assert_called_once()
    assert isinstance(state, Idle)


# ---------------------------------------------------------------------------
# STOP
# ---------------------------------------------------------------------------


def test_handle_stop_action(handle_tag_event, mock_player):
    state = Paused(tag="test-tag", paused_at=40.0)
    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)

    mock_player.stop.assert_called_once()
    assert isinstance(new_state, Idle)
    assert new_state.retry is None


# ---------------------------------------------------------------------------
# CONTINUE / WAITING / IDLE
# ---------------------------------------------------------------------------


def test_handle_continue_action(handle_tag_event, mock_player):
    state = Waiting(tag="test-tag", removed_at=95.0)
    new_state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), state)

    mock_player.play.assert_not_called()
    mock_player.pause.assert_not_called()
    mock_player.resume.assert_not_called()
    mock_player.stop.assert_not_called()
    assert isinstance(new_state, Playing)
    assert new_state.tag == "test-tag"


def test_handle_waiting_action(handle_tag_event, mock_player):
    state = Playing(tag="test-tag")
    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.25), state)

    mock_player.play.assert_not_called()
    mock_player.pause.assert_not_called()
    mock_player.resume.assert_not_called()
    mock_player.stop.assert_not_called()
    assert isinstance(new_state, Waiting)
    assert new_state.removed_at == pytest.approx(100.25)


def test_handle_waiting_preserves_removal_timestamp_on_subsequent_occurrences(handle_tag_event, mock_player):
    state = Waiting(tag="test-tag", removed_at=99.25)
    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.25), state)

    mock_player.pause.assert_not_called()
    assert isinstance(new_state, Waiting)
    assert new_state.removed_at == pytest.approx(99.25)


def test_handle_idle_action(handle_tag_event):
    state = Idle()
    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.25), state)
    assert isinstance(new_state, Idle)


def test_unregistered_tag_while_paused_should_not_resume(handle_tag_event, mock_player, mock_library):
    """Regression: paused + unknown tag -> no play/resume."""
    state = Paused(tag="good-tag", paused_at=10.0)
    mock_library.get_disc.return_value = None

    state = handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.0), state)
    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()

    state = handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.5), state)
    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()


def test_same_tag_detection_resets_logical_removal_grace_period(handle_tag_event, mock_player):
    state = Playing(tag="test-tag")

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    assert isinstance(state, Waiting)
    assert state.removed_at == pytest.approx(100.0)

    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.5), state)
    assert isinstance(state, Playing)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=103.2), state)
    mock_player.pause.assert_not_called()
    assert isinstance(state, Waiting)
    assert state.removed_at == pytest.approx(103.2)


def test_same_tag_returns_after_pause_resumes_immediately(handle_tag_event, mock_player):
    state = Playing(tag="test-tag")

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.1), state)
    assert isinstance(state, Waiting)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=103.2), state)
    mock_player.pause.assert_called_once()
    assert isinstance(state, Paused)
    assert state.paused_at == pytest.approx(103.2)

    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=103.3), state)
    mock_player.resume.assert_called_once()
    assert isinstance(state, Playing)
    assert state.tag == "test-tag"
    assert state.retry is None


# ---------------------------------------------------------------------------
# Retry - PLAY
# ---------------------------------------------------------------------------


def test_handle_play_action_does_not_update_state_when_player_raises(handle_tag_event, mock_player):
    mock_player.play.side_effect = PlaybackError("bad uri")
    new_state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), Idle())

    mock_player.play.assert_called_once()
    assert isinstance(new_state, Idle)
    assert new_state.retry is not None
    assert new_state.retry.action == "play"
    assert new_state.retry.tag_id == "test-tag"


def test_handle_play_failure_does_not_throttle_different_tag(handle_tag_event, mock_player):
    mock_player.play.side_effect = [PlaybackError("bad uri"), None]

    state = handle_tag_event.execute(TagEvent(tag_id="tag-a", timestamp=100.0), Idle())
    state = handle_tag_event.execute(TagEvent(tag_id="tag-b", timestamp=100.2), state)

    assert mock_player.play.call_count == 2
    assert isinstance(state, Playing)
    assert state.tag == "tag-b"
    assert state.retry is None


def test_handle_play_failure_keeps_retry_after_brief_missed_read(handle_tag_event, mock_player):
    mock_player.play.side_effect = PlaybackError("bad uri")

    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), Idle())
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.04), state)
    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.05), state)

    mock_player.play.assert_called_once()
    assert isinstance(state, Idle)
    assert state.retry is not None
    assert state.retry.action == "play"
    assert state.retry.tag_id == "test-tag"
    assert state.retry.next_retry_at == pytest.approx(100.1)


def test_handle_play_failure_gives_up_after_retry_delays_are_exhausted(mock_player, mock_library):
    ctx = TransitionContext(pause_delay=3, max_pause_duration=50, retry_delays=(0.5,))
    hte = HandleTagEvent(player=mock_player, library=mock_library, ctx=ctx)
    mock_player.play.side_effect = PlaybackError("bad uri")

    state = hte.execute(TagEvent(tag_id="test-tag", timestamp=100.0), Idle())
    state = hte.execute(TagEvent(tag_id="test-tag", timestamp=100.5), state)
    state = hte.execute(TagEvent(tag_id="test-tag", timestamp=101.0), state)

    assert mock_player.play.call_count == 2
    assert isinstance(state, Idle)
    assert state.retry is not None
    assert state.retry.action == "play"
    assert state.retry.tag_id == "test-tag"
    assert state.retry.attempt_count == 2
    assert state.retry.exhausted is True
    assert state.retry.next_retry_at is None


def test_handle_play_failure_clears_retry_when_unknown_tag_is_read(handle_tag_event, mock_player, mock_library):
    known_disc = Disc(uri="uri:tag-a", metadata=DiscMetadata(), option=DiscOption(shuffle=False))
    mock_library.get_disc.side_effect = lambda tag_id: known_disc if tag_id == "tag-a" else None
    mock_player.play.side_effect = PlaybackError("bad uri")

    state = handle_tag_event.execute(TagEvent(tag_id="tag-a", timestamp=100.0), Idle())
    assert isinstance(state, Idle)
    assert state.retry is not None
    assert state.retry.tag_id == "tag-a"

    state = handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.2), state)
    assert state.retry is None

    state = handle_tag_event.execute(TagEvent(tag_id="tag-a", timestamp=100.3), state)
    assert mock_player.play.call_count == 2
    assert isinstance(state, Idle)
    assert state.retry is not None
    assert state.retry.tag_id == "tag-a"


# ---------------------------------------------------------------------------
# Retry - RESUME
# ---------------------------------------------------------------------------


def test_handle_resume_action_does_not_update_state_when_player_raises(handle_tag_event, mock_player):
    mock_player.resume.side_effect = PlaybackError("cannot resume")
    state = Paused(tag="test-tag", paused_at=60.0)

    new_state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), state)

    mock_player.resume.assert_called_once()
    assert isinstance(new_state, Paused)
    assert new_state.paused_at == pytest.approx(60.0)
    assert new_state.retry is not None
    assert new_state.retry.action == "resume"
    assert new_state.retry.tag_id is None


def test_handle_resume_failure_keeps_retry_after_brief_missed_read(handle_tag_event, mock_player):
    mock_player.resume.side_effect = PlaybackError("cannot resume")
    state = Paused(tag="test-tag", paused_at=60.0)

    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.04), state)
    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.05), state)

    mock_player.resume.assert_called_once()
    assert isinstance(state, Paused)
    assert state.retry is not None
    assert state.retry.action == "resume"
    assert state.retry.tag_id is None
    assert state.retry.next_retry_at == pytest.approx(100.1)


# ---------------------------------------------------------------------------
# Retry - PAUSE
# ---------------------------------------------------------------------------


def test_handle_pause_action_does_not_update_state_when_player_raises(handle_tag_event, mock_player):
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)

    mock_player.pause.assert_called_once()
    assert isinstance(new_state, Waiting)
    assert new_state.tag == "test-tag"
    assert new_state.removed_at == pytest.approx(96.9)
    assert new_state.retry is not None
    assert new_state.retry.action == "pause"
    assert new_state.retry.tag_id is None
    assert new_state.retry.attempt_count == 1
    assert new_state.retry.next_retry_at == pytest.approx(100.1)


def test_handle_pause_failure_does_not_retry_before_backoff_expires(handle_tag_event, mock_player):
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.05), state)

    mock_player.pause.assert_called_once()
    assert isinstance(state, Waiting)
    assert state.retry is not None
    assert state.retry.attempt_count == 1


def test_handle_pause_failure_retries_after_backoff_and_updates_state_on_success(handle_tag_event, mock_player):
    mock_player.pause.side_effect = [PlaybackError("cannot pause"), None]
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.1), state)

    assert mock_player.pause.call_count == 2
    assert isinstance(state, Paused)
    assert state.paused_at == pytest.approx(100.1)
    assert state.retry is None


def test_handle_pause_failure_uses_next_backoff_after_retry_fails(handle_tag_event, mock_player):
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.1), state)

    assert mock_player.pause.call_count == 2
    assert isinstance(state, Waiting)
    assert state.retry is not None
    assert state.retry.attempt_count == 2
    assert state.retry.next_retry_at == pytest.approx(100.35)


def test_handle_pause_failure_gives_up_after_retry_delays_are_exhausted(mock_player, mock_library):
    ctx = TransitionContext(pause_delay=3, max_pause_duration=50, retry_delays=(0.5,))
    hte = HandleTagEvent(player=mock_player, library=mock_library, ctx=ctx)
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = hte.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = hte.execute(TagEvent(tag_id=None, timestamp=100.5), state)
    state = hte.execute(TagEvent(tag_id=None, timestamp=200.0), state)

    assert mock_player.pause.call_count == 2
    mock_player.stop.assert_not_called()
    assert isinstance(state, Waiting)
    assert state.retry is not None
    assert state.retry.action == "pause"
    assert state.retry.attempt_count == 2
    assert state.retry.exhausted is True
    assert state.retry.next_retry_at is None


def test_persistent_pause_failure_keeps_retrying_pause_after_pause_duration(handle_tag_event, mock_player):
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.5), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=1000.0), state)

    assert mock_player.pause.call_count == 3
    mock_player.stop.assert_not_called()
    assert isinstance(state, Waiting)
    assert state.retry is not None
    assert state.retry.action == "pause"
    assert state.retry.attempt_count == 3
    assert state.retry.next_retry_at == pytest.approx(1000.5)


def test_handle_pause_failure_clears_retry_when_action_changes(handle_tag_event, mock_player):
    mock_player.pause.side_effect = PlaybackError("cannot pause")
    state = Waiting(tag="test-tag", removed_at=96.9)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.2), state)

    mock_player.pause.assert_called_once()
    assert isinstance(state, Playing)
    assert state.retry is None


# ---------------------------------------------------------------------------
# Retry - STOP
# ---------------------------------------------------------------------------


def test_handle_stop_action_does_not_update_state_when_player_raises(handle_tag_event, mock_player):
    mock_player.stop.side_effect = PlaybackError("cannot stop")
    state = Paused(tag="test-tag", paused_at=49.0)

    new_state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)

    mock_player.stop.assert_called_once()
    assert isinstance(new_state, Paused)
    assert new_state.tag == "test-tag"
    assert new_state.paused_at == pytest.approx(49.0)
    assert new_state.retry is not None
    assert new_state.retry.action == "stop"
    assert new_state.retry.tag_id is None


def test_handle_stop_failure_does_not_retry_before_backoff_expires(handle_tag_event, mock_player):
    mock_player.stop.side_effect = PlaybackError("cannot stop")
    state = Paused(tag="test-tag", paused_at=49.0)

    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.05), state)

    mock_player.stop.assert_called_once()
    assert isinstance(state, Paused)
    assert state.tag == "test-tag"
    assert state.paused_at == pytest.approx(49.0)
    assert state.retry is not None
    assert state.retry.attempt_count == 1


def test_handle_stop_failure_gives_up_after_retry_delays_are_exhausted(mock_player, mock_library):
    ctx = TransitionContext(pause_delay=3, max_pause_duration=50, retry_delays=(0.5,))
    hte = HandleTagEvent(player=mock_player, library=mock_library, ctx=ctx)
    mock_player.stop.side_effect = PlaybackError("cannot stop")
    state = Paused(tag="test-tag", paused_at=49.0)

    state = hte.execute(TagEvent(tag_id=None, timestamp=100.0), state)
    state = hte.execute(TagEvent(tag_id=None, timestamp=100.5), state)
    state = hte.execute(TagEvent(tag_id=None, timestamp=200.0), state)

    assert mock_player.stop.call_count == 2
    assert isinstance(state, Paused)
    assert state.retry is not None
    assert state.retry.action == "stop"
    assert state.retry.attempt_count == 2
    assert state.retry.exhausted is True
    assert state.retry.next_retry_at is None
