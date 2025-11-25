import builtins
import logging
from unittest.mock import patch

import pytest

from jukebox.adapters.outbound.readers.dryrun_reader_adapter import DryrunReaderAdapter


def test_init_creates_reader(caplog):
    """Should initialize the adapter."""
    caplog.set_level(logging.INFO, logger="jukebox")

    adapter = DryrunReaderAdapter()

    assert adapter.counter == 0
    assert adapter.uid is None
    assert "Creating dryrun reader" in caplog.text


@pytest.mark.parametrize(
    "input, expected_uid, expected_counter",
    [("uri", "uri", 0), ("uri_with_counter 20", "uri_with_counter", 20)],
)
def test_read(monkeypatch, input, expected_uid, expected_counter):
    """Should read the tag uid and counter."""
    monkeypatch.setattr(builtins, "input", lambda: input)

    adapter = DryrunReaderAdapter()

    result = adapter.read()

    assert adapter.uid == expected_uid
    assert adapter.counter == expected_counter
    assert result == expected_uid


@pytest.mark.parametrize(
    "input, expected_error",
    [
        (
            "too_many_args 10 dummy",
            "Invalid input, should be `tag_uid counter`, received: ['too_many_args', '10', 'dummy']",
        ),
        (
            "too_many_args   20",
            "Invalid input, should be `tag_uid counter`, received: ['too_many_args', '', '', '20']",
        ),
        ("negative_integer -2", "Counter parameter should be a positive integer, received: `-2`"),
        ("not_an_integer dummy", "Counter parameter should be a positive integer, received: `dummy`"),
    ],
)
def test_read_invalid_input(monkeypatch, caplog, input, expected_error):
    """Should raise a warning when the input is invalid."""
    monkeypatch.setattr(builtins, "input", lambda: input)

    adapter = DryrunReaderAdapter()

    with caplog.at_level(logging.WARNING):
        result = adapter.read()

    assert adapter.uid is None
    assert adapter.counter == 0
    assert result is None
    assert expected_error in caplog.text


def test_read_with_counter():
    """Should read the tag uid and decrement the counter until it reaches 0."""
    adapter = DryrunReaderAdapter()
    adapter.uid = "uri"
    adapter.counter = 10

    assert adapter.uid == "uri"
    assert adapter.counter == 10

    for expected_counter in range(adapter.counter - 1, -1, -1):
        result = adapter.read()
        assert adapter.uid == "uri"
        assert adapter.counter == expected_counter
        assert result == "uri"

    with patch("builtins.input", return_value="uri") as mock_input:
        result = adapter.read()
        mock_input.assert_called_once()
        assert adapter.uid == "uri"
        assert adapter.counter == 0
        assert result == "uri"
