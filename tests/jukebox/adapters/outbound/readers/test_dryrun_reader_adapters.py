import logging
import sys
from unittest.mock import patch

import pytest

from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter


class FakeStdin:
    def __init__(self, line: str):
        self.line = line

    def readline(self):
        return self.line


def test_init_creates_reader(caplog):
    """Should initialize the adapter."""
    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunReaderAdapter()

    assert adapter.hold_until is None
    assert adapter.uid is None
    assert "Creating dryrun reader" in caplog.text


@pytest.mark.parametrize(
    "input, now, expected_uid, expected_hold_until",
    [("uri", 100.0, "uri", None), ("uri_with_duration 2.5", 100.0, "uri_with_duration", 102.5)],
)
def test_read(monkeypatch, input, now, expected_uid, expected_hold_until):
    """Should read the tag uid and optional hold duration."""
    fake_stdin = FakeStdin(f"{input}\n")
    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.select.select", lambda *args: ([fake_stdin], [], []))
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.time.monotonic", lambda: now)

    adapter = DryrunReaderAdapter()

    result = adapter.read()

    assert adapter.uid == expected_uid
    assert adapter.hold_until == expected_hold_until
    assert result == expected_uid


@pytest.mark.parametrize(
    "input, expected_error",
    [
        (
            "too_many_args 10 dummy",
            "Invalid input, should be `tag_uid duration_seconds`, received: ['too_many_args', '10', 'dummy']",
        ),
        (
            "too_many_args   20",
            "Invalid input, should be `tag_uid duration_seconds`, received: ['too_many_args', '', '', '20']",
        ),
        ("negative_duration -2", "Duration parameter should be a non-negative number of seconds, received: `-2`"),
        ("not_a_number dummy", "Duration parameter should be a non-negative number of seconds, received: `dummy`"),
    ],
)
def test_read_invalid_input(monkeypatch, caplog, input, expected_error):
    """Should raise a warning when the input is invalid."""
    fake_stdin = FakeStdin(f"{input}\n")
    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.select.select", lambda *args: ([fake_stdin], [], []))
    monkeypatch.setattr(sys, "stdin", fake_stdin)

    adapter = DryrunReaderAdapter()

    with caplog.at_level(logging.WARNING):
        result = adapter.read()

    assert adapter.uid is None
    assert adapter.hold_until is None
    assert result is None
    assert expected_error in caplog.text


def test_read_with_duration(monkeypatch):
    """Should keep returning the tag until the hold duration expires."""
    adapter = DryrunReaderAdapter()
    adapter.uid = "uri"
    adapter.hold_until = 102.0

    assert adapter.uid == "uri"
    assert adapter.hold_until == 102.0

    for now in (100.0, 100.5, 101.99):
        monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.time.monotonic", lambda: now)
        result = adapter.read()
        assert adapter.uid == "uri"
        assert adapter.hold_until == 102.0
        assert result == "uri"

    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.time.monotonic", lambda: 102.0)
    fake_stdin = FakeStdin("uri\n")
    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.select.select", lambda *args: ([fake_stdin], [], []))
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    with patch.object(fake_stdin, "readline", wraps=fake_stdin.readline) as mock_readline:
        result = adapter.read()
        mock_readline.assert_called_once()
        assert adapter.uid == "uri"
        assert adapter.hold_until is None
        assert result == "uri"


def test_read_returns_none_when_no_input_is_ready(monkeypatch):
    """Should return None without attempting to consume stdin."""
    fake_stdin = FakeStdin("uri\n")
    monkeypatch.setattr("jukebox.adapters.outbound.readers.dryrun_reader_adapter.select.select", lambda *args: ([], [], []))
    monkeypatch.setattr(sys, "stdin", fake_stdin)

    adapter = DryrunReaderAdapter()
    with patch.object(fake_stdin, "readline", wraps=fake_stdin.readline) as mock_readline:
        result = adapter.read()

    assert result is None
    mock_readline.assert_not_called()
