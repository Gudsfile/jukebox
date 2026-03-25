from unittest.mock import MagicMock, call

import pytest

from jukebox.domain.entities import CurrentTagAction, Disc, DiscMetadata, DiscOption, PlaybackSession, TagEvent
from jukebox.domain.use_cases.determine_action import DetermineAction
from jukebox.domain.use_cases.determine_current_tag_action import DetermineCurrentTagAction
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent


@pytest.fixture
def mock_player():
    """Create a mock player."""
    return MagicMock()


@pytest.fixture
def mock_library():
    """Create a mock library."""
    library = MagicMock()
    # Default: return a disc
    library.get_disc.return_value = Disc(
        uri="uri:123",
        metadata=DiscMetadata(artist="Test Artist", album="Test Album", track="Test Track"),
        option=DiscOption(shuffle=False),
    )
    return library


@pytest.fixture
def determine_action():
    """Create a DetermineAction instance."""
    return DetermineAction(pause_delay=3, max_pause_duration=50)


@pytest.fixture
def determine_current_tag_action():
    """Create a DetermineCurrentTagAction instance."""
    return DetermineCurrentTagAction()


@pytest.fixture
def mock_current_tag_repository():
    return MagicMock()


@pytest.fixture
def handle_tag_event(
    mock_player, mock_library, mock_current_tag_repository, determine_action, determine_current_tag_action
):
    """Create a HandleTagEvent instance."""
    return HandleTagEvent(
        player=mock_player,
        library=mock_library,
        current_tag_repository=mock_current_tag_repository,
        determine_action=determine_action,
        determine_current_tag_action=determine_current_tag_action,
    )


def test_handle_play_action_with_existing_disc(handle_tag_event, mock_player, mock_library):
    """Should play disc when action is PLAY and disc exists."""
    session = PlaybackSession()
    tag_event = TagEvent(tag_id="test-tag", timestamp=100.0)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_library.get_disc.assert_called_once_with("test-tag")

    mock_player.play.assert_called_once_with("uri:123", False)

    assert new_session.playing_tag == "test-tag"
    assert new_session.paused_at is None
    assert new_session.playing_tag_removed_at is None


def test_known_tag_writes_current_tag(handle_tag_event, mock_current_tag_repository, mock_library):
    session = PlaybackSession()

    handle_tag_event.execute(TagEvent(tag_id="known-tag", timestamp=100.0), session)

    mock_library.get_disc.assert_called_once_with("known-tag")
    mock_current_tag_repository.set.assert_called_once_with("known-tag")


def test_unknown_tag_writes_current_tag(handle_tag_event, mock_current_tag_repository, mock_library):
    mock_library.get_disc.return_value = None
    session = PlaybackSession()

    handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.0), session)

    mock_current_tag_repository.set.assert_called_once_with("unknown-tag")


def test_same_tag_does_not_rewrite_current_tag_unnecessarily(handle_tag_event, mock_current_tag_repository):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="same-tag", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="same-tag", timestamp=100.2), session)

    assert mock_current_tag_repository.set.call_count == 1
    assert session.physical_tag == "same-tag"


def test_different_tag_replaces_current_tag_state(handle_tag_event, mock_current_tag_repository):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="tag-a", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="tag-b", timestamp=100.2), session)

    assert mock_current_tag_repository.set.call_args_list == [
        call("tag-a"),
        call("tag-b"),
    ]
    assert session.physical_tag == "tag-b"


def test_current_tag_survives_brief_missed_reads_and_clears_after_absence_grace(
    handle_tag_event, mock_current_tag_repository
):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="tag-1", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.4), session)

    mock_current_tag_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at == pytest.approx(100.4)

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.6), session)
    mock_current_tag_repository.clear.assert_not_called()
    assert session.physical_tag_removed_at == pytest.approx(100.4)

    session = handle_tag_event.execute(TagEvent(tag_id="tag-1", timestamp=100.8), session)
    assert mock_current_tag_repository.set.call_count == 1
    assert session.physical_tag_removed_at is None

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=101.9), session)

    mock_current_tag_repository.clear.assert_called_once_with()
    assert session.physical_tag is None


def test_unknown_tag_promotes_to_known_without_rewriting_current_tag(
    handle_tag_event, mock_current_tag_repository, mock_library, mock_player
):
    promoted_disc = Disc(uri="uri:promoted", metadata=DiscMetadata(), option=DiscOption(shuffle=True))
    mock_library.get_disc.side_effect = [None, promoted_disc]
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.2), session)

    mock_current_tag_repository.set.assert_called_once_with("promote-tag")
    mock_player.play.assert_called_once_with("uri:promoted", True)
    assert session.playing_tag == "promote-tag"


def test_current_tag_set_failure_does_not_block_playback(handle_tag_event, mock_current_tag_repository, mock_player):
    mock_current_tag_repository.set.side_effect = OSError("disk full")
    session = PlaybackSession()

    new_session = handle_tag_event.execute(TagEvent(tag_id="known-tag", timestamp=100.0), session)

    mock_player.play.assert_called_once_with("uri:123", False)
    assert new_session.playing_tag == "known-tag"


def test_current_tag_clear_failure_does_not_block_pause(handle_tag_event, mock_current_tag_repository, mock_player):
    handle_tag_event.determine_action.pause_delay = 0.25
    mock_current_tag_repository.clear.side_effect = OSError("permission denied")
    session = PlaybackSession(
        playing_tag="known-tag",
        physical_tag="known-tag",
        physical_tag_removed_at=0.99,
        playing_tag_removed_at=0.24,
        last_event_timestamp=100.0,
    )

    new_session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.02), session)

    mock_player.pause.assert_called_once()
    assert new_session.paused_at == 100.02


def test_handle_play_action_with_shuffle(handle_tag_event, mock_player, mock_library):
    """Should play with shuffle when disc has shuffle option."""
    mock_library.get_disc.return_value = Disc(
        uri="uri:456",
        metadata=DiscMetadata(),
        option=DiscOption(shuffle=True),
    )

    session = PlaybackSession()
    tag_event = TagEvent(tag_id="shuffle-tag", timestamp=100.0)

    handle_tag_event.execute(tag_event, session)

    mock_player.play.assert_called_once_with("uri:456", True)


def test_handle_play_action_with_nonexistent_disc(handle_tag_event, mock_player, mock_library):
    """Should not play when disc doesn't exist."""
    mock_library.get_disc.return_value = None

    session = PlaybackSession()
    tag_event = TagEvent(tag_id="unknown-tag", timestamp=100.0)

    handle_tag_event.execute(tag_event, session)

    mock_player.play.assert_not_called()


def test_handle_resume_action(handle_tag_event, mock_player):
    """Should resume player when action is RESUME."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=90.0,
    )
    tag_event = TagEvent(tag_id="test-tag", timestamp=100.0)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.resume.assert_called_once()
    assert new_session.paused_at is None
    assert new_session.playing_tag_removed_at is None


def test_handle_pause_action(handle_tag_event, mock_player):
    """Should pause player when action is PAUSE."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=None,
        playing_tag_removed_at=5.0,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.2)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_called_once()
    assert new_session.paused_at == 100.2
    assert new_session.playing_tag_removed_at == 5.0


def test_handle_pause_then_stop_after_max_pause_duration(handle_tag_event, mock_player):
    """Should set paused_at on PAUSE and eventually stop after max_pause_duration."""
    handle_tag_event.determine_action.pause_delay = 0.25
    handle_tag_event.determine_action.max_pause_duration = 0.5

    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=None,
        playing_tag_removed_at=99.76,
        last_event_timestamp=100.0,
    )

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.02), session)
    assert session.paused_at == pytest.approx(100.02)
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.32), session)
    assert session.paused_at == pytest.approx(100.02)  # unchanged
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.62), session)
    mock_player.stop.assert_called_once()
    assert session.paused_at is None
    assert session.playing_tag is None


def test_handle_stop_action(handle_tag_event, mock_player):
    """Should stop player when action is STOP."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=40.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.0)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.stop.assert_called_once()
    assert new_session.playing_tag is None
    assert new_session.paused_at is None
    assert new_session.playing_tag_removed_at is None


def test_handle_continue_action(handle_tag_event, mock_player):
    """Should not call player when action is CONTINUE."""
    session = PlaybackSession(
        playing_tag="test-tag",
        playing_tag_removed_at=95.0,
    )
    tag_event = TagEvent(tag_id="test-tag", timestamp=100.0)

    new_session = handle_tag_event.execute(tag_event, session)

    # No player methods should be called
    mock_player.play.assert_not_called()
    mock_player.pause.assert_not_called()
    mock_player.resume.assert_not_called()
    mock_player.stop.assert_not_called()

    assert new_session.playing_tag_removed_at is None


def test_handle_waiting_action(handle_tag_event, mock_player):
    """Should record tag removal timestamp when action is WAITING."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=None,
        playing_tag_removed_at=None,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.25)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.play.assert_not_called()
    mock_player.pause.assert_not_called()
    mock_player.resume.assert_not_called()
    mock_player.stop.assert_not_called()

    assert new_session.playing_tag_removed_at == 100.25


def test_handle_waiting_preserves_removal_timestamp_on_subsequent_occurrences(handle_tag_event, mock_player):
    """Should not overwrite removal timestamp on subsequent grace period events."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=None,
        playing_tag_removed_at=99.25,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.25)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_not_called()

    assert new_session.playing_tag_removed_at == 99.25


def test_handle_idle_action(handle_tag_event):
    """Should not overwrite paused timestamp when action is IDLE."""
    session = PlaybackSession(
        paused_at=10.0,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.25)

    new_session = handle_tag_event.execute(tag_event, session)

    assert new_session.paused_at == 10.0


def test_unregistered_tag_while_paused_should_not_resume(handle_tag_event, mock_player, mock_library):
    """Should NOT resume playback when an unregistered tag is read while paused.

    Regression test for bug: When paused and a tag with no disc is read,
    the player would incorrectly resume the previous disc on subsequent reads.
    """
    session = PlaybackSession(
        playing_tag="good-tag",
        paused_at=10.0,  # Paused
    )

    mock_library.get_disc.return_value = None
    bad_tag_event = TagEvent(tag_id="unknown-tag", timestamp=100.0)

    session = handle_tag_event.execute(bad_tag_event, session)

    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()

    bad_tag_event2 = TagEvent(tag_id="unknown-tag", timestamp=bad_tag_event.timestamp + 0.5)
    session = handle_tag_event.execute(bad_tag_event2, session)

    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()


def test_set_action_with_missing_tag_id_logs_error_and_does_nothing(
    handle_tag_event,
    mock_current_tag_repository,
    caplog,
):
    """Defensive test: SET with None tag_id should never occur in normal flow."""
    session = PlaybackSession()

    session.physical_tag = "existing-tag"
    session.physical_tag_removed_at = 1.23

    with caplog.at_level("ERROR", logger="jukebox"):
        handle_tag_event._apply_current_tag_action(
            CurrentTagAction.SET,
            TagEvent(tag_id=None, timestamp=100.0),
            session,
        )

    mock_current_tag_repository.set.assert_not_called()

    assert "`SET` action without tag_id" in caplog.text
    assert session.physical_tag == "existing-tag"
    assert session.physical_tag_removed_at == 1.23


def test_same_tag_detection_resets_logical_removal_grace_period(handle_tag_event, mock_player):
    """Should restart the logical grace period after the same tag is seen again."""
    session = PlaybackSession(
        playing_tag="test-tag",
        paused_at=None,
        playing_tag_removed_at=None,
        last_event_timestamp=99.75,
    )

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.0), session)
    assert session.playing_tag_removed_at == 100.0

    session = handle_tag_event.execute(TagEvent(tag_id="test-tag", timestamp=100.5), session)
    assert session.playing_tag_removed_at is None

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=103.2), session)

    mock_player.pause.assert_not_called()
    assert session.paused_at is None
    assert session.playing_tag_removed_at == 103.2
