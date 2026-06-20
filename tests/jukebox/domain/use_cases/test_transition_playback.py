import pytest

from jukebox.domain.entities import (
    Disc,
    DiscMetadata,
    DiscOption,
    Idle,
    Paused,
    PlaybackCommand,
    Playing,
    RetryState,
    TagEvent,
    TransitionContext,
    Waiting,
)
from jukebox.domain.use_cases.transition_playback import transition

CTX = TransitionContext(pause_delay=3.0, max_pause_duration=50.0, retry_delays=(0.1, 0.5, 1.0))
DISC = Disc(uri="uri:1", metadata=DiscMetadata(), option=DiscOption())
NO_DISC_FOUND: None = None  # tag not registered in library


def _event(tag_id: str | None, timestamp: float = 100.0) -> TagEvent:
    return TagEvent(tag_id=tag_id, timestamp=timestamp)


def _retry(action: PlaybackCommand, tag_id: str | None = None) -> RetryState:
    return RetryState(
        action=action,
        tag_id=tag_id,
        first_failed_at=99.0,
        last_failed_at=99.0,
        attempt_count=1,
        next_retry_at=99.1,
    )


# ---------------------------------------------------------------------------
# From Idle
# ---------------------------------------------------------------------------


def test_idle_tag_with_disc_returns_playing_and_play_command():
    state, cmd = transition(Idle(), _event("tag-1"), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd == "play"


def test_idle_no_tag_stays_idle():
    state, cmd = transition(Idle(), _event(None), NO_DISC_FOUND, CTX)
    assert state == Idle()
    assert cmd is None


def test_idle_unregistered_tag_stays_idle():
    state, cmd = transition(Idle(), _event("tag-1"), NO_DISC_FOUND, CTX)
    assert state == Idle()
    assert cmd is None


def test_idle_unregistered_tag_clears_play_retry():
    idle = Idle(retry=_retry("play", "tag-1"))
    state, cmd = transition(idle, _event("tag-1"), NO_DISC_FOUND, CTX)
    assert state == Idle(retry=None)
    assert cmd is None


def test_idle_with_pending_retry_preserved_when_no_tag():
    idle = Idle(retry=_retry("play", "tag-1"))
    state, cmd = transition(idle, _event(None), NO_DISC_FOUND, CTX)
    assert state is idle
    assert cmd is None


def test_idle_with_pending_retry_new_disc_returns_fresh_playing():
    idle = Idle(retry=_retry("play", "tag-1"))
    state, cmd = transition(idle, _event("tag-1"), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd == "play"


# ---------------------------------------------------------------------------
# From Playing
# ---------------------------------------------------------------------------


def test_playing_same_tag_returns_fresh_playing_no_command():
    state, cmd = transition(Playing(tag="tag-1"), _event("tag-1"), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd is None


def test_playing_same_tag_clears_any_pending_retry():
    playing = Playing(tag="tag-1", retry=_retry("play", "tag-2"))
    state, cmd = transition(playing, _event("tag-1"), DISC, CTX)
    assert state == Playing(tag="tag-1", retry=None)
    assert cmd is None


def test_playing_tag_removed_enters_waiting():
    state, cmd = transition(Playing(tag="tag-1"), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state == Waiting(tag="tag-1", removed_at=100.0)
    assert cmd is None


def test_playing_different_tag_with_disc_returns_play():
    state, cmd = transition(Playing(tag="tag-1"), _event("tag-2"), DISC, CTX)
    assert state == Playing(tag="tag-2")
    assert cmd == "play"


def test_playing_unregistered_tag_clears_cross_tag_retry():
    # Unknown tag with no disc clears any pending cross-tag retry.
    playing = Playing(tag="tag-1", retry=_retry("play", "tag-2"))
    state, cmd = transition(playing, _event("tag-2"), NO_DISC_FOUND, CTX)
    assert state == Playing(tag="tag-1", retry=None)
    assert cmd is None


def test_playing_unregistered_tag_no_retry():
    state, cmd = transition(Playing(tag="tag-1"), _event("tag-2"), NO_DISC_FOUND, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd is None


# ---------------------------------------------------------------------------
# From Waiting
# ---------------------------------------------------------------------------


def test_waiting_same_tag_returns_playing_no_command():
    state, cmd = transition(Waiting(tag="tag-1", removed_at=98.0), _event("tag-1", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd is None


def test_waiting_same_tag_clears_pause_retry():
    waiting = Waiting(tag="tag-1", removed_at=98.0, retry=_retry("pause"))
    state, cmd = transition(waiting, _event("tag-1", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-1", retry=None)
    assert cmd is None


def test_waiting_within_grace_period_stays():
    # removed_at=98.0, timestamp=100.0 -> 2s elapsed < 3s pause_delay
    waiting = Waiting(tag="tag-1", removed_at=98.0)
    state, cmd = transition(waiting, _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state is waiting
    assert cmd is None


def test_waiting_grace_period_expired_returns_paused_and_pause_command():
    # removed_at=96.0, timestamp=100.0 -> 4s elapsed > 3s pause_delay
    state, cmd = transition(Waiting(tag="tag-1", removed_at=96.0), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state == Paused(tag="tag-1", paused_at=100.0)
    assert cmd == "pause"


def test_waiting_different_tag_with_disc_returns_play():
    state, cmd = transition(Waiting(tag="tag-1", removed_at=98.0), _event("tag-2", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-2")
    assert cmd == "play"


def test_waiting_unregistered_tag_clears_retry():
    # Unknown tag with no disc clears any pending retry, removal timestamp preserved.
    waiting = Waiting(tag="tag-1", removed_at=98.0, retry=_retry("pause"))
    state, cmd = transition(waiting, _event("tag-2", 100.0), NO_DISC_FOUND, CTX)
    assert state == Waiting(tag="tag-1", removed_at=98.0, retry=None)
    assert cmd is None


def test_waiting_unregistered_tag_no_retry():
    waiting = Waiting(tag="tag-1", removed_at=98.0)
    state, cmd = transition(waiting, _event("tag-2", 100.0), NO_DISC_FOUND, CTX)
    assert state == Waiting(tag="tag-1", removed_at=98.0)
    assert cmd is None


# ---------------------------------------------------------------------------
# From Paused
# ---------------------------------------------------------------------------


def test_paused_same_tag_within_max_returns_playing_and_resume():
    # paused_at=80.0, timestamp=100.0 -> 20s < 50s max_pause_duration
    state, cmd = transition(Paused(tag="tag-1", paused_at=80.0), _event("tag-1", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd == "resume"


def test_paused_same_tag_max_exceeded_returns_playing_and_play():
    # paused_at=40.0, timestamp=100.0 -> 60s > 50s max_pause_duration
    state, cmd = transition(Paused(tag="tag-1", paused_at=40.0), _event("tag-1", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd == "play"


def test_paused_different_tag_with_disc_returns_play():
    state, cmd = transition(Paused(tag="tag-1", paused_at=80.0), _event("tag-2", 100.0), DISC, CTX)
    assert state == Playing(tag="tag-2")
    assert cmd == "play"


def test_paused_unregistered_tag_clears_retry():
    # Unknown tag with no disc clears any pending retry, paused_at preserved.
    paused = Paused(tag="tag-1", paused_at=80.0, retry=_retry("resume"))
    state, cmd = transition(paused, _event("tag-2", 100.0), NO_DISC_FOUND, CTX)
    assert state == Paused(tag="tag-1", paused_at=80.0, retry=None)
    assert cmd is None


def test_paused_unregistered_tag_no_retry():
    paused = Paused(tag="tag-1", paused_at=80.0)
    state, cmd = transition(paused, _event("tag-2", 100.0), NO_DISC_FOUND, CTX)
    assert state == Paused(tag="tag-1", paused_at=80.0)
    assert cmd is None


def test_paused_no_tag_within_max_stays():
    paused = Paused(tag="tag-1", paused_at=80.0)
    state, cmd = transition(paused, _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state is paused
    assert cmd is None


def test_paused_no_tag_max_exceeded_returns_idle_and_stop():
    # paused_at=40.0, timestamp=100.0 -> 60s > 50s
    state, cmd = transition(Paused(tag="tag-1", paused_at=40.0), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state == Idle()
    assert cmd == "stop"


def test_paused_same_tag_max_exceeded_no_disc_stays_paused():
    # Disc removed from library while paused: can't restart, stays paused.
    # paused_at=40.0, timestamp=100.0 -> 60s > 50s, but no disc to play
    state, cmd = transition(Paused(tag="tag-1", paused_at=40.0), _event("tag-1", 100.0), NO_DISC_FOUND, CTX)
    assert state == Paused(tag="tag-1", paused_at=40.0)
    assert cmd is None


def test_paused_same_unregistered_tag_still_resumes():
    # RESUME doesn't need the disc, the player holds its own paused state.
    # Even if the disc was removed from the library, the player can still resume.
    state, cmd = transition(Paused(tag="tag-1", paused_at=80.0), _event("tag-1", 100.0), NO_DISC_FOUND, CTX)
    assert state == Playing(tag="tag-1")
    assert cmd == "resume"


def test_paused_with_retry_no_tag_within_max_preserves_retry():
    retry = _retry("resume")
    paused = Paused(tag="tag-1", paused_at=80.0, retry=retry)
    state, cmd = transition(paused, _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert state is paused  # same instance, retry preserved
    assert cmd is None


# ---------------------------------------------------------------------------
# Grace period boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("paused_seconds_ago", [49.9, 25.0, 0.1])
def test_paused_within_max_pause_boundary(paused_seconds_ago):
    paused_at = 100.0 - paused_seconds_ago
    state, cmd = transition(Paused(tag="tag-1", paused_at=paused_at), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert isinstance(state, Paused)
    assert cmd is None


@pytest.mark.parametrize("paused_seconds_ago", [50.0, 50.1, 200.0])
def test_paused_past_max_pause_boundary(paused_seconds_ago):
    paused_at = 100.0 - paused_seconds_ago
    state, cmd = transition(Paused(tag="tag-1", paused_at=paused_at), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert isinstance(state, Idle)
    assert cmd == "stop"


@pytest.mark.parametrize("removal_seconds_ago", [2.9, 1.0, 0.0])
def test_waiting_within_grace_boundary(removal_seconds_ago):
    removed_at = 100.0 - removal_seconds_ago
    state, cmd = transition(Waiting(tag="tag-1", removed_at=removed_at), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert isinstance(state, Waiting)
    assert cmd is None


@pytest.mark.parametrize("removal_seconds_ago", [3.0, 3.1, 10.0])
def test_waiting_past_grace_boundary(removal_seconds_ago):
    removed_at = 100.0 - removal_seconds_ago
    state, cmd = transition(Waiting(tag="tag-1", removed_at=removed_at), _event(None, 100.0), NO_DISC_FOUND, CTX)
    assert isinstance(state, Paused)
    assert cmd == "pause"
