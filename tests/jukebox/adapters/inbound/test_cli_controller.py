from unittest.mock import create_autospec, patch

import pytest

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.domain.entities import CurrentTagSession, PlaybackSession
from jukebox.domain.ports import ReaderPort
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent
from jukebox.domain.use_cases.sync_current_tag import SyncCurrentTag


def _make_controller(reader, handle_tag_event, sync_current_tag=None, loop_interval_seconds=0.1):
    if sync_current_tag is None:
        sync_current_tag = create_autospec(SyncCurrentTag, instance=True, spec_set=True)
    return CLIController(
        reader=reader,
        handle_tag_event=handle_tag_event,
        sync_current_tag=sync_current_tag,
        loop_interval_seconds=loop_interval_seconds,
    )


def test_run_sleeps_only_for_remaining_loop_interval():
    reader = create_autospec(ReaderPort, instance=True, spec_set=True)
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = create_autospec(HandleTagEvent, instance=True, spec_set=True)
    handle_tag_event.execute.return_value = PlaybackSession()
    controller = _make_controller(reader=reader, handle_tag_event=handle_tag_event)

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.03, 100.04, 100.1]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_called_once_with(pytest.approx(0.06))
    handle_tag_event.execute.assert_called_once()


def test_run_skips_sleep_when_reader_already_used_the_interval():
    reader = create_autospec(ReaderPort, instance=True, spec_set=True)
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = create_autospec(HandleTagEvent, instance=True, spec_set=True)
    handle_tag_event.execute.return_value = PlaybackSession()
    controller = _make_controller(reader=reader, handle_tag_event=handle_tag_event)

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.11, 100.12, 100.2]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_not_called()
    handle_tag_event.execute.assert_called_once()


def test_sync_current_tag_called_before_handle_tag_event():
    call_order = []
    captured_sessions = []
    reader = create_autospec(ReaderPort, instance=True, spec_set=True)
    reader.read.side_effect = ["tag-1", "tag-1", KeyboardInterrupt()]
    handle_tag_event = create_autospec(HandleTagEvent, instance=True, spec_set=True)
    handle_tag_event.execute.side_effect = lambda *_: call_order.append("handle") or PlaybackSession()
    sync_current_tag = create_autospec(SyncCurrentTag, instance=True, spec_set=True)
    sync_current_tag.execute.side_effect = lambda _ev, sess: (call_order.append("sync"), captured_sessions.append(sess))
    controller = _make_controller(reader=reader, handle_tag_event=handle_tag_event, sync_current_tag=sync_current_tag)

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", return_value=100.0),
        patch("jukebox.adapters.inbound.cli_controller.sleep"),
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    assert call_order == ["sync", "handle", "sync", "handle"]
    assert all(isinstance(s, CurrentTagSession) for s in captured_sessions)
    assert captured_sessions[0] is captured_sessions[1]
