import time
from unittest.mock import MagicMock

import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from jukebox.domain.entities import PlaybackSession, TagEvent
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
def handle_tag_event(mock_player, mock_library, determine_action):
    """Create a HandleTagEvent instance."""
    return HandleTagEvent(
        player=mock_player,
        library=mock_library,
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
    )
    tag_event = TagEvent(tag_id=None, timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_called_once()
    assert new_session.awaiting_seconds == 0.5
    assert new_session.tag_removed_seconds == 0
    assert new_session.is_paused is True
    assert new_session.current_tag == "test-tag"


def test_handle_stop_action(handle_tag_event, mock_player):
    """Should stop player when action is STOP."""
    session = PlaybackSession(
        current_tag="test-tag",
        previous_tag="test-tag",
        awaiting_seconds=100.0,
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
    )
    tag_event = TagEvent(tag_id=None, timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    mock_player.pause.assert_not_called()

    assert new_session.tag_removed_seconds == 1.5


def test_handle_idle_action(handle_tag_event, mock_player):
    """Should increment awaiting_seconds when action is IDLE."""
    session = PlaybackSession(
        awaiting_seconds=10.0,
    )
    tag_event = TagEvent(tag_id=None, timestamp=time.time())

    new_session = handle_tag_event.execute(tag_event, session)

    assert new_session.awaiting_seconds == 10.5
