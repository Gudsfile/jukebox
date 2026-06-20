from unittest.mock import MagicMock

import pytest

from jukebox.domain.entities import NoTag, TagEvent, TagPresent, TagRemoved
from jukebox.domain.entities.current_tag_state import CurrentTagContext
from jukebox.domain.use_cases.sync_current_tag import SyncCurrentTag


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def ctx():
    return CurrentTagContext(grace_seconds=1.0)


@pytest.fixture
def sync(mock_repository, ctx):
    return SyncCurrentTag(repository=mock_repository, ctx=ctx)


def _execute(sync: SyncCurrentTag, state, tag_id, timestamp):
    return sync.execute(TagEvent(tag_id=tag_id, timestamp=timestamp), state)


# ---------------------------------------------------------------------------
# Repository calls
# ---------------------------------------------------------------------------


def test_set_command_calls_repository_set(sync, mock_repository):
    state = _execute(sync, NoTag(), "tag-1", 100.0)

    mock_repository.set.assert_called_once_with("tag-1")
    assert isinstance(state, TagPresent)
    assert state.tag == "tag-1"


def test_clear_command_calls_repository_clear(sync, mock_repository):
    prior = TagPresent(tag="tag-1", last_event_timestamp=99.0)
    state = _execute(sync, prior, None, 100.0)

    mock_repository.clear.assert_called_once_with()
    assert isinstance(state, NoTag)


def test_no_command_does_not_touch_repository(sync, mock_repository):
    prior = TagPresent(tag="tag-1", last_event_timestamp=100.0)
    state = _execute(sync, prior, "tag-1", 100.1)

    mock_repository.set.assert_not_called()
    mock_repository.clear.assert_not_called()
    assert isinstance(state, TagPresent)
    assert state.tag == "tag-1"


# ---------------------------------------------------------------------------
# last_event_timestamp stamping
# ---------------------------------------------------------------------------


def test_last_event_timestamp_stamped_on_success(sync):
    state = _execute(sync, NoTag(), None, 100.5)
    assert state.last_event_timestamp == pytest.approx(100.5)


def test_last_event_timestamp_stamped_on_repository_failure(sync, mock_repository):
    mock_repository.set.side_effect = OSError("disk full")
    prior = NoTag()
    state = _execute(sync, prior, "tag-1", 100.5)

    assert state.last_event_timestamp == pytest.approx(100.5)
    assert isinstance(state, NoTag)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_swallows_repository_set_error_and_returns_prior_state(sync, mock_repository):
    mock_repository.set.side_effect = RuntimeError("network error")
    prior = NoTag()

    state = _execute(sync, prior, "tag-1", 100.0)

    assert isinstance(state, NoTag)


def test_swallows_repository_clear_error_and_returns_prior_state(sync, mock_repository):
    mock_repository.clear.side_effect = OSError("disk full")
    prior = TagPresent(tag="tag-1", last_event_timestamp=99.0)

    state = _execute(sync, prior, None, 100.0)

    assert isinstance(state, TagPresent)
    assert state.tag == "tag-1"


# ---------------------------------------------------------------------------
# Integration sequence
# ---------------------------------------------------------------------------


def test_tag_survives_brief_missed_reads_and_clears_after_grace(sync, mock_repository):
    state = NoTag()

    state = _execute(sync, state, "tag-1", 100.0)
    mock_repository.set.assert_called_once_with("tag-1")

    state = _execute(sync, state, None, 100.4)
    mock_repository.clear.assert_not_called()
    assert isinstance(state, TagRemoved)
    assert state.removed_at == pytest.approx(100.4)

    state = _execute(sync, state, None, 100.6)
    mock_repository.clear.assert_not_called()
    assert isinstance(state, TagRemoved)

    state = _execute(sync, state, "tag-1", 100.8)
    assert mock_repository.set.call_count == 1
    assert isinstance(state, TagPresent)

    state = _execute(sync, state, None, 101.9)
    mock_repository.clear.assert_called_once_with()
    assert isinstance(state, NoTag)


def test_keep_does_not_rewrite_repository(sync, mock_repository):
    state = NoTag()
    state = _execute(sync, state, "tag-1", 100.0)
    state = _execute(sync, state, "tag-1", 100.2)

    assert mock_repository.set.call_count == 1
    assert isinstance(state, TagPresent)
    assert state.tag == "tag-1"
