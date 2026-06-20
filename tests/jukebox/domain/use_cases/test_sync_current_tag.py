from unittest.mock import MagicMock

import pytest

from jukebox.domain.entities import CurrentTagAction, CurrentTagSession, TagEvent
from jukebox.domain.use_cases.apply_current_tag_action import ApplyCurrentTagAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction
from jukebox.domain.use_cases.sync_current_tag import SyncCurrentTag


@pytest.fixture
def mock_determine():
    determine = MagicMock(spec=DetermineCurrentTagAction)
    determine.execute.return_value = CurrentTagAction.SET
    return determine


@pytest.fixture
def mock_apply():
    return MagicMock(spec=ApplyCurrentTagAction)


@pytest.fixture
def sync(mock_determine, mock_apply):
    return SyncCurrentTag(
        determine_current_tag_action=mock_determine,
        apply_current_tag_action=mock_apply,
    )


def test_execute_calls_determine_then_apply(sync, mock_determine, mock_apply):
    session = CurrentTagSession()
    event = TagEvent(tag_id="tag-1", timestamp=100.0)

    sync.execute(event, session)

    mock_determine.execute.assert_called_once_with(event, session)
    mock_apply.execute.assert_called_once_with(CurrentTagAction.SET, event, session)
    assert session.last_event_timestamp == pytest.approx(100.0)


def test_execute_swallows_exception_from_determine(sync, mock_determine, mock_apply):
    mock_determine.execute.side_effect = RuntimeError("boom")
    session = CurrentTagSession()

    sync.execute(TagEvent(tag_id="tag-1", timestamp=100.0), session)

    mock_apply.execute.assert_not_called()
    assert session.last_event_timestamp == pytest.approx(100.0)


def test_execute_swallows_exception_from_apply(sync, mock_determine, mock_apply):
    mock_apply.execute.side_effect = OSError("disk full")
    session = CurrentTagSession()

    sync.execute(TagEvent(tag_id="tag-1", timestamp=100.0), session)

    assert session.last_event_timestamp == pytest.approx(100.0)


# Integration tests — real use cases, mock repository only


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def sync_integration(mock_repository):
    return SyncCurrentTag(
        determine_current_tag_action=DetermineCurrentTagAction(),
        apply_current_tag_action=ApplyCurrentTagAction(current_tag_repository=mock_repository),
    )


def _sync(sync_integration, session, tag_id, timestamp):
    """Simulate one SyncCurrentTag loop tick."""
    sync_integration.execute(TagEvent(tag_id=tag_id, timestamp=timestamp), session)


def test_current_tag_survives_brief_missed_reads_and_clears_after_absence_grace(sync_integration, mock_repository):
    session = CurrentTagSession()

    _sync(sync_integration, session, "tag-1", 100.0)
    _sync(sync_integration, session, None, 100.4)

    mock_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at == pytest.approx(100.4)

    _sync(sync_integration, session, None, 100.6)
    mock_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at == pytest.approx(100.4)

    _sync(sync_integration, session, "tag-1", 100.8)
    assert mock_repository.set.call_count == 1
    assert session.physical_tag_removed_at is None

    _sync(sync_integration, session, None, 101.9)

    mock_repository.clear.assert_called_once_with()
    assert session.physical_tag is None


def test_keep_action_does_not_rewrite_repository(sync_integration, mock_repository):
    session = CurrentTagSession()

    _sync(sync_integration, session, "tag-1", 100.0)
    _sync(sync_integration, session, "tag-1", 100.2)

    assert mock_repository.set.call_count == 1
    assert session.physical_tag == "tag-1"
