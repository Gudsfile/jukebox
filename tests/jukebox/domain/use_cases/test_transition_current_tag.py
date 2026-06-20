from jukebox.domain.entities import NoTag, TagEvent, TagPresent, TagRemoved
from jukebox.domain.entities.current_tag_state import CurrentTagContext
from jukebox.domain.use_cases.transition_current_tag import transition_current_tag

CTX = CurrentTagContext(grace_seconds=1.0)


def _event(tag_id: str | None, timestamp: float = 100.0) -> TagEvent:
    return TagEvent(tag_id=tag_id, timestamp=timestamp)


# ---------------------------------------------------------------------------
# From NoTag
# ---------------------------------------------------------------------------


def test_no_tag_tag_arrives_returns_tag_present_and_set():
    state, cmd = transition_current_tag(NoTag(), _event("tag-1"), CTX)
    assert state == TagPresent(tag="tag-1")
    assert cmd == "set"


def test_no_tag_no_tag_stays_no_tag():
    state, cmd = transition_current_tag(NoTag(), _event(None), CTX)
    assert state == NoTag()
    assert cmd is None


# ---------------------------------------------------------------------------
# From TagPresent
# ---------------------------------------------------------------------------


def test_tag_present_same_tag_stays_tag_present():
    state, cmd = transition_current_tag(TagPresent(tag="tag-1"), _event("tag-1"), CTX)
    assert state == TagPresent(tag="tag-1")
    assert cmd is None


def test_tag_present_different_tag_returns_new_tag_present_and_set():
    state, cmd = transition_current_tag(TagPresent(tag="tag-1"), _event("tag-2"), CTX)
    assert state == TagPresent(tag="tag-2")
    assert cmd == "set"


def test_tag_present_no_tag_within_grace_returns_tag_removed():
    prior = TagPresent(tag="tag-1", last_event_timestamp=99.5)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == TagRemoved(tag="tag-1", removed_at=100.0)
    assert cmd is None


def test_tag_present_no_tag_gap_equals_grace_clears():
    prior = TagPresent(tag="tag-1", last_event_timestamp=99.0)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == NoTag()
    assert cmd == "clear"


def test_tag_present_no_tag_gap_beyond_grace_clears():
    prior = TagPresent(tag="tag-1", last_event_timestamp=95.0)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == NoTag()
    assert cmd == "clear"


def test_tag_present_no_tag_no_last_event_timestamp_treats_as_micro_interruption():
    prior = TagPresent(tag="tag-1", last_event_timestamp=None)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == TagRemoved(tag="tag-1", removed_at=100.0)
    assert cmd is None


# ---------------------------------------------------------------------------
# From TagRemoved
# ---------------------------------------------------------------------------


def test_tag_removed_same_tag_returns_tag_present():
    prior = TagRemoved(tag="tag-1", removed_at=99.5)
    state, cmd = transition_current_tag(prior, _event("tag-1"), CTX)
    assert state == TagPresent(tag="tag-1")
    assert cmd is None


def test_tag_removed_different_tag_returns_new_tag_present_and_set():
    prior = TagRemoved(tag="tag-1", removed_at=99.5)
    state, cmd = transition_current_tag(prior, _event("tag-2"), CTX)
    assert state == TagPresent(tag="tag-2")
    assert cmd == "set"


def test_tag_removed_no_tag_within_grace_stays_tag_removed():
    prior = TagRemoved(tag="tag-1", removed_at=99.5)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == prior
    assert cmd is None


def test_tag_removed_no_tag_grace_expired_returns_no_tag_and_clear():
    prior = TagRemoved(tag="tag-1", removed_at=98.0)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == NoTag()
    assert cmd == "clear"


def test_tag_removed_no_tag_exactly_at_grace_boundary_clears():
    prior = TagRemoved(tag="tag-1", removed_at=99.0)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == NoTag()
    assert cmd == "clear"


def test_tag_removed_no_tag_just_before_grace_boundary_stays():
    prior = TagRemoved(tag="tag-1", removed_at=99.1)
    state, cmd = transition_current_tag(prior, _event(None, timestamp=100.0), CTX)
    assert state == prior
    assert cmd is None


# ---------------------------------------------------------------------------
# End-to-end sequence: tag survives brief miss then clears after extended absence
# ---------------------------------------------------------------------------


def test_tag_survives_brief_missed_read_and_clears_after_grace():
    state: NoTag | TagPresent | TagRemoved = NoTag()

    state, cmd = transition_current_tag(state, _event("tag-1", 100.0), CTX)
    assert cmd == "set"

    # Executor stamps last_event_timestamp = 100.0
    state = TagPresent(tag="tag-1", last_event_timestamp=100.0)

    state, cmd = transition_current_tag(state, _event(None, 100.4), CTX)
    assert isinstance(state, TagRemoved)
    assert cmd is None

    # Executor stamps last_event_timestamp = 100.4
    state = TagRemoved(tag="tag-1", removed_at=100.4, last_event_timestamp=100.4)

    state, cmd = transition_current_tag(state, _event(None, 100.6), CTX)
    assert isinstance(state, TagRemoved)
    assert cmd is None

    state = TagRemoved(tag="tag-1", removed_at=100.4, last_event_timestamp=100.6)

    state, cmd = transition_current_tag(state, _event("tag-1", 100.8), CTX)
    assert state == TagPresent(tag="tag-1")
    assert cmd is None

    state = TagPresent(tag="tag-1", last_event_timestamp=100.8)

    state, cmd = transition_current_tag(state, _event(None, 101.9), CTX)
    assert state == NoTag()
    assert cmd == "clear"
