from unittest.mock import create_autospec, patch

import pytest

from jukebox.adapters.inbound.cli_controller import CLIController
from jukebox.domain.entities import PlaybackSession
from jukebox.domain.ports import ReaderPort
from jukebox.domain.repositories import CurrentDiscRepository
from jukebox.domain.use_cases.handle_tag_event import HandleTagEvent


def test_run_sleeps_only_for_remaining_loop_interval():
    reader = create_autospec(ReaderPort, instance=True, spec_set=True)
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = create_autospec(HandleTagEvent, instance=True, spec_set=True)
    handle_tag_event.execute.return_value = PlaybackSession()
    current_disc_repository = create_autospec(CurrentDiscRepository, instance=True, spec_set=True)
    controller = CLIController(
        reader=reader,
        handle_tag_event=handle_tag_event,
        current_disc_repository=current_disc_repository,
        loop_interval_seconds=0.1,
    )

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.03, 100.04, 100.1]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_called_once_with(pytest.approx(0.06))
    handle_tag_event.execute.assert_called_once()
    assert current_disc_repository.clear.call_count == 2


def test_run_skips_sleep_when_reader_already_used_the_interval():
    reader = create_autospec(ReaderPort, instance=True, spec_set=True)
    reader.read.side_effect = ["tag-1", KeyboardInterrupt()]
    handle_tag_event = create_autospec(HandleTagEvent, instance=True, spec_set=True)
    handle_tag_event.execute.return_value = PlaybackSession()
    current_disc_repository = create_autospec(CurrentDiscRepository, instance=True, spec_set=True)
    controller = CLIController(
        reader=reader,
        handle_tag_event=handle_tag_event,
        current_disc_repository=current_disc_repository,
        loop_interval_seconds=0.1,
    )

    with (
        patch("jukebox.adapters.inbound.cli_controller.time.monotonic", side_effect=[100.0, 100.11, 100.12, 100.2]),
        patch("jukebox.adapters.inbound.cli_controller.sleep") as mock_sleep,
        pytest.raises(KeyboardInterrupt),
    ):
        controller.run()

    mock_sleep.assert_not_called()
    handle_tag_event.execute.assert_called_once()
    assert current_disc_repository.clear.call_count == 2
