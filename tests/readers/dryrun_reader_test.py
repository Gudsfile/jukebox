import logging
from unittest.mock import patch

import pytest

from jukebox.readers.dryrun import DryRunReader


@pytest.fixture()
def reader():
    yield DryRunReader()


def test_init(reader):
    assert reader.uid is None
    assert reader.repeat == 0


@pytest.mark.parametrize(
    "input, expected_uid, expected_repeat",
    [("uri", "uri", 0), ("uri_with_repeat 20", "uri_with_repeat", 20)],
)
def test_read(monkeypatch, reader, input, expected_uid, expected_repeat):
    monkeypatch.setattr("builtins.input", lambda: input)
    result = reader.read()

    assert reader.uid == expected_uid
    assert reader.repeat == expected_repeat
    assert result == expected_uid


@pytest.mark.parametrize(
    "input, expected_error",
    [
        (
            "too_many_args 10 dummy",
            "Invalid input, should be `tag_uid repeat`, received: ['too_many_args', '10', 'dummy']",
        ),
        ("too_many_args   20", "Invalid input, should be `tag_uid repeat`, received: ['too_many_args', '', '', '20']"),
        ("negative_integer -2", "Repeat parameter should be a positive integer, received: `-2`"),
        ("not_an_integer dummy", "Repeat parameter should be a positive integer, received: `dummy`"),
    ],
)
def test_read_invalid_input(monkeypatch, caplog, reader, input, expected_error):
    monkeypatch.setattr("builtins.input", lambda: input)
    with caplog.at_level(logging.WARNING):
        result = reader.read()

    assert reader.uid is None
    assert reader.repeat == 0
    assert result is None
    assert expected_error in caplog.text


def test_read_with_repeat(reader):
    reader.uid = "uri"
    reader.repeat = 10
    for expected_repeat in range(reader.repeat - 1, -1, -1):
        result = reader.read()
        assert reader.uid == "uri"
        assert reader.repeat == expected_repeat
        assert result == "uri"
    with patch("builtins.input", return_value="uri") as mock_input:
        result = reader.read()
        mock_input.assert_called_once()
        assert reader.uid == "uri"
        assert reader.repeat == 0
        assert result == "uri"
