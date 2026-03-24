import pytest

from jukebox.domain.entities import PlaybackAction, PlaybackSession, TagEvent
from jukebox.domain.use_cases.determine_action import DetermineAction


@pytest.fixture
def determine_action():
    """Create a DetermineAction instance with standard parameters."""
    return DetermineAction(pause_delay=3, max_pause_duration=50)


def test_continue_when_same_tag_and_not_paused(determine_action):
    """Should continue when detecting same tag and not paused."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=None,
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id="id-1", timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.CONTINUE


def test_resume_when_same_tag_and_paused(determine_action):
    """Should resume when detecting same tag and paused with acceptable duration."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=80.0,  # Paused but < max_pause_duration
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id="id-1", timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.RESUME


def test_play_when_different_tag(determine_action):
    """Should play when detecting a different tag."""
    session = PlaybackSession(
        playing_tag="id-2",
        paused_at=None,
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id="id-1", timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.PLAY


def test_play_when_new_tag(determine_action):
    """Should play when detecting a tag for the first time."""
    session = PlaybackSession(
        playing_tag=None,
        paused_at=None,
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id="id-1", timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.PLAY


def test_waiting_when_tag_just_be_removed(determine_action):
    """Should wait when tag has just been removed."""
    session = PlaybackSession(playing_tag="id-1", paused_at=None, playing_tag_removed_at=None)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.WAITING


def test_waiting_when_tag_removed_within_grace_period(determine_action):
    """Should wait when tag removed but within grace period."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=None,
        playing_tag_removed_at=98.0,  # < pause_delay (3)
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.WAITING


def test_pause_when_tag_removed_after_grace_period(determine_action):
    """Should pause when tag removed and grace period expired."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=None,
        playing_tag_removed_at=95.0,  # > pause_delay (3)
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.PAUSE


def test_stop_when_paused_too_long(determine_action):
    """Should stop when paused duration exceeds maximum."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=40.0,  # > max_pause_duration (50)
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.STOP


def test_idle_when_no_tag_and_no_playing_tag(determine_action):
    """Should idle when no tag detected and no previous tag."""
    session = PlaybackSession(
        playing_tag=None,
        paused_at=10.0,
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.IDLE


def test_play_when_same_tag_but_paused_too_long(determine_action):
    """Should play (restart) when same tag but paused duration exceeded maximum."""
    session = PlaybackSession(
        playing_tag="id-1",
        paused_at=40.0,  # > max_pause_duration (50)
        playing_tag_removed_at=None,
    )
    tag_event = TagEvent(tag_id="id-1", timestamp=100.0)

    action = determine_action.execute(tag_event, session)

    assert action == PlaybackAction.PLAY
