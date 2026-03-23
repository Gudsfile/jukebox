import pytest

from jukebox.domain.entities import CurrentTagAction, PlaybackSession, TagEvent
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction


@pytest.fixture
def determine_current_tag_action():
    return DetermineCurrentTagAction(grace_seconds=1.0)


def test_keep_when_same_tag_already_physical(determine_current_tag_action):
    """Should keep when tag is present and matches the current physical tag."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=None)
    tag_event = TagEvent(tag_id="tag-1", timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.KEEP


@pytest.mark.parametrize("physical_tag_removed_at", (None, 50.0, 99.5, 100.0, 105.0, 150.0))
def test_set_when_new_tag_detected(determine_current_tag_action, physical_tag_removed_at):
    """Should set when a tag is present but different from the current physical tag"""
    session = PlaybackSession(physical_tag=None, physical_tag_removed_at=physical_tag_removed_at)
    tag_event = TagEvent(tag_id="tag-1", timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.SET


@pytest.mark.parametrize("physical_tag_removed_at", (None, 50.0, 99.5, 100.0, 105.0, 150.0))
def test_set_when_different_tag_replaces_physical(determine_current_tag_action, physical_tag_removed_at):
    """Should set when a different tag replaces the existing physical tag."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=physical_tag_removed_at)
    tag_event = TagEvent(tag_id="tag-2", timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.SET


@pytest.mark.parametrize("physical_tag_removed_at", (None, 50.0, 99.5, 100.0, 105.0, 150.0))
def test_keep_when_no_tag_and_no_physical_tag(determine_current_tag_action, physical_tag_removed_at):
    """Should keep when no tag is detected and no physical tag is tracked."""
    session = PlaybackSession(physical_tag=None, physical_tag_removed_at=physical_tag_removed_at)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.KEEP


def test_remove_when_tag_just_removed_within_grace_period(determine_current_tag_action):
    """Should remove when tag disappears and removal has not been recorded yet."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=None, last_event_timestamp=99.5)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.REMOVE


def test_keep_when_no_tag_within_grace_period(determine_current_tag_action):
    """Should keep when no tag is detected but still within the grace period."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=99.95)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.KEEP


def test_clear_when_no_tag_after_grace_period(determine_current_tag_action):
    """Should clear when no tag is detected and the grace period has elapsed."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=99.0)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.CLEAR


def test_grace_period_boundary_is_exclusive(determine_current_tag_action):
    """Should keep at exactly the grace boundary (strictly less than)."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=99.1)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.KEEP


def test_restore_when_tag_returns_after_removal(determine_current_tag_action):
    """Should restore when tag is detected and the still within the grace period."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=100.0)
    tag_event = TagEvent(tag_id="tag-1", timestamp=100.5)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.RESTORE


def test_clear_when_tag_just_removed_after_grace_period(determine_current_tag_action):
    """Should clear when no tag is detected and removal has not been recorded yet but the grace period has elapsed."""
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=None, last_event_timestamp=99.0)
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    action = determine_current_tag_action.execute(tag_event, session)

    assert action == CurrentTagAction.CLEAR
