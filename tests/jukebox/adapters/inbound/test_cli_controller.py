from unittest.mock import MagicMock, patch

import pytest

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.domain.entities import PlaybackSession


def test_run_sleeps_only_for_remaining_loop_interval():
    reader = MagicMock()
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = MagicMock(return_value=PlaybackSession())
    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event, loop_interval_seconds=0.1)

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.03, 100.04, 100.1]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_called_once_with(pytest.approx(0.06))
    handle_tag_event.execute.assert_called_once()


def test_run_skips_sleep_when_reader_already_used_the_interval():
    reader = MagicMock()
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = MagicMock(return_value=PlaybackSession())
    controller = CLIController(reader=reader, handle_tag_event=handle_tag_event, loop_interval_seconds=0.1)

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.11, 100.12, 100.2]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_not_called()
    handle_tag_event.execute.assert_called_once()
