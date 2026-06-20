import dataclasses

import pytest

from jukebox.domain.entities import NoTag, TagPresent, TagRemoved
from jukebox.domain.entities.current_tag_state import CurrentTagContext


@pytest.mark.parametrize(
    "state",
    [
        NoTag(),
        TagPresent(tag="tag-1"),
        TagRemoved(tag="tag-1", removed_at=100.0),
    ],
)
def test_states_raise_on_mutation(state):
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.last_event_timestamp = 0.0


def test_no_tag_defaults():
    state = NoTag()
    assert state.last_event_timestamp is None


def test_tag_present_defaults():
    state = TagPresent(tag="tag-1")
    assert state.tag == "tag-1"
    assert state.last_event_timestamp is None


def test_tag_removed_fields():
    state = TagRemoved(tag="tag-1", removed_at=99.5)
    assert state.tag == "tag-1"
    assert state.removed_at == pytest.approx(99.5)
    assert state.last_event_timestamp is None


def test_current_tag_context_is_frozen():
    ctx = CurrentTagContext(grace_seconds=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.grace_seconds = 2.0  # ty: ignore[invalid-assignment]
