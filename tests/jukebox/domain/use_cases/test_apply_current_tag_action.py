from unittest.mock import MagicMock

import pytest

from jukebox.domain.entities import CurrentTagAction, PlaybackSession, TagEvent
from jukebox.domain.use_cases.apply_current_tag_action import ApplyCurrentTagAction


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def apply(mock_repository):
    return ApplyCurrentTagAction(current_tag_repository=mock_repository)


def test_set_writes_repository_and_updates_session(apply, mock_repository):
    session = PlaybackSession(physical_tag_removed_at=1.0)
    apply.execute(CurrentTagAction.SET, TagEvent(tag_id="tag-1", timestamp=100.0), session)

    mock_repository.set.assert_called_once_with("tag-1")
    assert session.physical_tag == "tag-1"
    assert session.physical_tag_removed_at is None


def test_set_with_none_tag_id_logs_error_and_does_nothing(apply, mock_repository, caplog):
    session = PlaybackSession(physical_tag="existing-tag", physical_tag_removed_at=1.23)

    with caplog.at_level("ERROR", logger="jukebox"):
        apply.execute(CurrentTagAction.SET, TagEvent(tag_id=None, timestamp=100.0), session)

    mock_repository.set.assert_not_called()
    assert "`SET` action without tag_id" in caplog.text
    assert session.physical_tag == "existing-tag"
    assert session.physical_tag_removed_at == 1.23


def test_clear_writes_repository_and_clears_session(apply, mock_repository):
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=1.0)
    apply.execute(CurrentTagAction.CLEAR, TagEvent(tag_id=None, timestamp=100.0), session)

    mock_repository.clear.assert_called_once_with()
    assert session.physical_tag is None
    assert session.physical_tag_removed_at is None


def test_restore_clears_removal_timestamp(apply, mock_repository):
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=99.0)
    apply.execute(CurrentTagAction.RESTORE, TagEvent(tag_id="tag-1", timestamp=100.0), session)

    mock_repository.set.assert_not_called()
    mock_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at is None


def test_remove_sets_removal_timestamp(apply, mock_repository):
    session = PlaybackSession(physical_tag="tag-1")
    apply.execute(CurrentTagAction.REMOVE, TagEvent(tag_id=None, timestamp=100.5), session)

    mock_repository.set.assert_not_called()
    mock_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at == pytest.approx(100.5)


def test_keep_does_nothing(apply, mock_repository):
    session = PlaybackSession(physical_tag="tag-1", physical_tag_removed_at=99.0)
    apply.execute(CurrentTagAction.KEEP, TagEvent(tag_id="tag-1", timestamp=100.0), session)

    mock_repository.set.assert_not_called()
    mock_repository.clear.assert_not_called()
    assert session.physical_tag == "tag-1"
    assert session.physical_tag_removed_at == 99.0
