import time
from unittest.mock import MagicMock, call

import pytest

from jukebox.domain.entities import CurrentDisc, Disc, DiscMetadata, DiscOption, PlaybackSession, TagEvent
from jukebox.domain.use_cases.determine_action import DetermineAction
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
def mock_current_disc_repository():
    repository = MagicMock()
    repository.clear_if_matches.return_value = True
    return repository


@pytest.fixture
def handle_tag_event(mock_player, mock_library, mock_current_disc_repository, determine_action):
    """Create a HandleTagEvent instance."""
    return HandleTagEvent(
        player=mock_player,
        library=mock_library,
        current_disc_repository=mock_current_disc_repository,
        determine_action=determine_action,
    )


def test_handle_play_action_with_existing_disc(handle_tag_event, mock_player, mock_library):
    """Should play disc when action is PLAY and disc exists."""
    session = PlaybackSession()
    tag_event = TagEvent(tag_id="test-tag", timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    mock_library.get_disc.assert_called_once_with("test-tag")

    mock_player.play.assert_called_once_with("uri:123", False)

    assert new_session.current_tag == "test-tag"
    assert new_session.previous_tag == "test-tag"
    assert new_session.awaiting_seconds == 0
    assert new_session.tag_removed_seconds == 0


def test_known_tag_writes_current_disc_with_known_in_library_true(
    handle_tag_event, mock_current_disc_repository, mock_library
):
    session = PlaybackSession()

    handle_tag_event.execute(TagEvent(tag_id="known-tag", timestamp=100.0), session)

    mock_library.get_disc.assert_called_once_with("known-tag")
    mock_current_disc_repository.save.assert_called_once_with(
        CurrentDisc(tag_id="known-tag", known_in_library=True)
    )


def test_unknown_tag_writes_current_disc_with_known_in_library_false(
    handle_tag_event, mock_current_disc_repository, mock_library
):
    mock_library.get_disc.return_value = None
    session = PlaybackSession()

    handle_tag_event.execute(TagEvent(tag_id="unknown-tag", timestamp=100.0), session)

    mock_current_disc_repository.save.assert_called_once_with(
        CurrentDisc(tag_id="unknown-tag", known_in_library=False)
    )


def test_same_tag_does_not_rewrite_current_disc_unnecessarily(
    handle_tag_event, mock_current_disc_repository
):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="same-tag", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="same-tag", timestamp=100.2), session)

    assert mock_current_disc_repository.save.call_count == 1
    assert session.physical_tag == "same-tag"
    assert session.physical_tag_known_in_library is True


def test_different_tag_replaces_current_disc_state(
    handle_tag_event, mock_current_disc_repository
):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="tag-a", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="tag-b", timestamp=100.2), session)

    assert mock_current_disc_repository.save.call_args_list == [
        call(CurrentDisc(tag_id="tag-a", known_in_library=True)),
        call(CurrentDisc(tag_id="tag-b", known_in_library=True)),
    ]
    assert session.physical_tag == "tag-b"


def test_current_disc_survives_brief_missed_reads_and_clears_after_absence_grace(
    handle_tag_event, mock_current_disc_repository
):
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="tag-1", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.4), session)

    mock_current_disc_repository.clear_if_matches.assert_not_called()

    session = handle_tag_event.execute(TagEvent(tag_id="tag-1", timestamp=100.8), session)
    assert mock_current_disc_repository.save.call_count == 1
    assert session.physical_tag_removed_seconds == 0.0

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=101.9), session)

    mock_current_disc_repository.clear_if_matches.assert_called_once_with("tag-1")
    assert session.physical_tag is None
    assert session.physical_tag_known_in_library is None


def test_unknown_tag_promotes_to_known_and_starts_playback_on_next_loop(
    handle_tag_event, mock_current_disc_repository, mock_library, mock_player
):
    promoted_disc = Disc(uri="uri:promoted", metadata=DiscMetadata(), option=DiscOption(shuffle=True))
    mock_library.get_disc.side_effect = [None, promoted_disc]
    session = PlaybackSession()

    session = handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.0), session)
    session = handle_tag_event.execute(TagEvent(tag_id="promote-tag", timestamp=100.2), session)

    assert mock_current_disc_repository.save.call_args_list == [
        call(CurrentDisc(tag_id="promote-tag", known_in_library=False)),
        call(CurrentDisc(tag_id="promote-tag", known_in_library=True)),
    ]
    mock_player.play.assert_called_once_with("uri:promoted", True)
    assert session.previous_tag == "promote-tag"
    assert session.current_tag == "promote-tag"


def test_current_disc_save_failure_does_not_block_playback(
    handle_tag_event, mock_current_disc_repository, mock_player
):
    mock_current_disc_repository.save.side_effect = OSError("disk full")
    session = PlaybackSession()

    new_session = handle_tag_event.execute(TagEvent(tag_id="known-tag", timestamp=100.0), session)

    mock_player.play.assert_called_once_with("uri:123", False)
    assert new_session.current_tag == "known-tag"
    assert new_session.previous_tag == "known-tag"


def test_current_disc_clear_failure_does_not_block_pause(
    handle_tag_event, mock_current_disc_repository, mock_player
):
    handle_tag_event.determine_action.pause_delay = 0.25
    mock_current_disc_repository.clear_if_matches.side_effect = OSError("permission denied")
    session = PlaybackSession(
        current_tag="known-tag",
        previous_tag="known-tag",
        physical_tag="known-tag",
        physical_tag_known_in_library=True,
        physical_tag_removed_seconds=0.99,
        tag_removed_seconds=0.24,
        last_event_timestamp=100.0,
    )

    new_session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.02), session)

    mock_player.pause.assert_called_once()
    assert new_session.is_paused is True


def test_handle_play_action_with_shuffle(handle_tag_event, mock_player, mock_library):
    """Should play with shuffle when disc has shuffle option."""
    mock_library.get_disc.return_value = Disc(
        uri="uri:456",
        metadata=DiscMetadata(),
        option=DiscOption(shuffle=True),
    )

    session = PlaybackSession()
    tag_event = TagEvent(tag_id="shuffle-tag", timestamp=time.time())

    handle_tag_event.execute(tag_event, session)

    mock_player.play.assert_called_once_with("uri:456", True)


def test_handle_play_action_with_nonexistent_disc(handle_tag_event, mock_player, mock_library):
    """Should not play when disc doesn't exist."""
    mock_library.get_disc.return_value = None

    session = PlaybackSession()
    tag_event = TagEvent(tag_id="unknown-tag", timestamp=time.time())

    handle_tag_event.execute(tag_event, session)

    mock_player.play.assert_not_called()


def test_handle_resume_action(handle_tag_event, mock_player):
    """Should resume player when action is RESUME."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=10.0,
        is_paused=True,
    )
    tag_event = TagEvent(tag_id="test-tag", timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.resume.assert_called_once()
    assert new_session.awaiting_seconds == 0
    assert new_session.tag_removed_seconds == 0
    assert new_session.current_tag == "test-tag"


def test_handle_pause_action(handle_tag_event, mock_player):
    """Should pause player when action is PAUSE."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=0.0,
        tag_removed_seconds=5.0,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.2)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_called_once()
    assert new_session.awaiting_seconds == 0.0
    assert new_session.tag_removed_seconds == 0
    assert new_session.is_paused is True
    assert new_session.current_tag == "test-tag"


def test_handle_pause_then_stop_after_max_pause_duration(handle_tag_event, mock_player):
    """Should accumulate paused time after PAUSE and eventually stop."""
    handle_tag_event.determine_action.pause_delay = 0.25
    handle_tag_event.determine_action.max_pause_duration = 0.5

    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=0.0,
        tag_removed_seconds=0.24,
        last_event_timestamp=100.0,
    )

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.02), session)

    assert session.awaiting_seconds == 0.0
    assert session.is_paused is True
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.32), session)

    assert session.awaiting_seconds == pytest.approx(0.3)
    assert session.is_paused is True
    mock_player.pause.assert_called_once()
    mock_player.stop.assert_not_called()

    session = handle_tag_event.execute(TagEvent(tag_id=None, timestamp=100.62), session)

    mock_player.stop.assert_called_once()
    assert session.awaiting_seconds == 0.0
    assert session.previous_tag is None
    assert session.current_tag is None
    assert session.is_paused is False


def test_handle_stop_action(handle_tag_event, mock_player):
    """Should stop player when action is STOP."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=100.0,
        is_paused=True,
    )
    tag_event = TagEvent(tag_id=None, timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.stop.assert_called_once()
    assert new_session.previous_tag is None
    assert new_session.current_tag is None
    assert new_session.is_paused is False
    assert new_session.tag_removed_seconds == 0


def test_handle_continue_action(handle_tag_event, mock_player):
    """Should not call player when action is CONTINUE."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=0.0,
    )
    tag_event = TagEvent(tag_id="test-tag", timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    # No player methods should be called
    mock_player.play.assert_not_called()
    mock_player.pause.assert_not_called()
    mock_player.resume.assert_not_called()
    mock_player.stop.assert_not_called()

    assert new_session.tag_removed_seconds == 0


def test_handle_waiting_action(handle_tag_event, mock_player):
    """Should increment tag_removed_seconds when action is WAITING."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=0.0,
        tag_removed_seconds=1.0,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.25)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_not_called()

    assert new_session.tag_removed_seconds == 1.25


def test_handle_idle_action(handle_tag_event, mock_player):
    """Should increment awaiting_seconds when action is IDLE."""
    session = PlaybackSession(
        awaiting_seconds=10.0,
        is_paused=True,
        last_event_timestamp=100.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=100.25)

    new_session = handle_tag_event.execute(tag_event, session)

    assert new_session.awaiting_seconds == 10.25


def test_handle_waiting_uses_elapsed_time(handle_tag_event, mock_player):
    """Should use elapsed timestamps for fractional grace periods."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=0.0,
        tag_removed_seconds=0.1,
        last_event_timestamp=50.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=50.15)

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_not_called()
    assert new_session.tag_removed_seconds == pytest.approx(0.25)


def test_unregistered_tag_while_paused_should_not_resume(handle_tag_event, mock_player, mock_library):
    """Should NOT resume playback when an unregistered tag is read while paused.

    Regression test for bug: When paused and a tag with no disc is read,
    the player would incorrectly resume the previous disc on subsequent reads.
    """
    session = PlaybackSession(
        current_tag="good-tag",
        previous_tag="good-tag",
        awaiting_seconds=10.0,  # Paused
        is_paused=True,
    )

    mock_library.get_disc.return_value = None
    bad_tag_event = TagEvent(tag_id="unknown-tag", timestamp=time.time())

    session = handle_tag_event.execute(bad_tag_event, session)

    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()

    bad_tag_event2 = TagEvent(tag_id="unknown-tag", timestamp=bad_tag_event.timestamp + 0.5)
    session = handle_tag_event.execute(bad_tag_event2, session)

    mock_player.play.assert_not_called()
    mock_player.resume.assert_not_called()
