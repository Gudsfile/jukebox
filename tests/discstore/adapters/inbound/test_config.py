import os
from unittest.mock import patch

import pytest

from discstore.adapters.inbound.config import (
    ApiCommand,
    CliAddCommand,
    CliEditCommand,
    CliListCommand,
    CliRemoveCommand,
    InteractiveCliCommand,
    parse_config,
)
from jukebox.shared.config_utils import DEFAULT_LIBRARY_PATH


@patch(
    "sys.argv",
    [
        "prog_name",
        "add",
        "my-tag",
        "/path/to/media.mp3",
        "--track",
        "My Song",
        "--artist",
        "The Testers",
        "--album",
        "Code Hits",
    ],
)
def test_parse_add_command():
    config = parse_config()

    assert config.verbose is False
    assert isinstance(config.command, CliAddCommand)
    assert config.command.type == "add"
    assert config.command.tag == "my-tag"
    assert config.command.uri == "/path/to/media.mp3"
    assert config.command.track == "My Song"
    assert config.command.artist == "The Testers"
    assert config.command.album == "Code Hits"


@patch("sys.argv", ["prog_name", "list", "line"])
def test_parse_list_command():
    config = parse_config()

    assert isinstance(config.command, CliListCommand)
    assert config.command.type == "list"
    assert config.command.mode == "line"


@patch("sys.argv", ["prog_name", "remove", "tag-to-delete"])
def test_parse_remove_command():
    config = parse_config()

    assert isinstance(config.command, CliRemoveCommand)
    assert config.command.type == "remove"
    assert config.command.tag == "tag-to-delete"


@patch(
    "sys.argv",
    [
        "prog_name",
        "edit",
        "my-tag",
        "--uri",
        "/path/to/media.mp3",
        "--track",
        "My Song",
        "--artist",
        "The Testers",
        "--album",
        "Code Hits",
    ],
)
def test_parse_edit_command():
    config = parse_config()

    assert config.verbose is False
    assert isinstance(config.command, CliEditCommand)
    assert config.command.type == "edit"
    assert config.command.tag == "my-tag"
    assert config.command.uri == "/path/to/media.mp3"
    assert config.command.track == "My Song"
    assert config.command.artist == "The Testers"
    assert config.command.album == "Code Hits"


@patch("sys.argv", ["prog_name", "api", "--port", "9999"])
def test_parse_api_command_with_port():
    config = parse_config()

    assert isinstance(config.command, ApiCommand)
    assert config.command.type == "api"
    assert config.command.port == 9999


@patch("sys.argv", ["prog_name", "interactive"])
def test_parse_interactive_command():
    config = parse_config()

    assert isinstance(config.command, InteractiveCliCommand)
    assert config.command.type == "interactive"


@patch("sys.argv", ["prog_name", "-v", "--library", "/custom/path.json", "list", "table"])
def test_verbose_and_library_flags():
    config = parse_config()

    assert config.verbose is True
    assert config.library == "/custom/path.json"


@patch.dict(os.environ, {"JUKEBOX_LIBRARY_PATH": "/env/path.json"})
@patch("logging.Logger.warning")
@patch("sys.argv", ["prog_name", "list", "table"])
def test_library_path_from_env_var(mock_warning):
    config = parse_config()

    assert config.library == "/env/path.json"
    assert mock_warning.call_count == 0


@patch.dict(os.environ, {"LIBRARY_PATH": "/env/path.json"})
@patch("logging.Logger.warning")
@patch("sys.argv", ["prog_name", "list", "table"])
def test_library_path_from_deprecated_env_var(mock_warning):
    config = parse_config()

    assert config.library == "/env/path.json"
    assert mock_warning.call_count == 1


@patch.dict(os.environ, {})
@patch("sys.argv", ["prog_name", "list", "table"])
def test_default_library_path():
    config = parse_config()

    assert config.library == DEFAULT_LIBRARY_PATH


@patch("sys.argv", ["prog_name", "add", "a-tag-without-a-uri"])
def test_validation_error_exits():
    with pytest.raises(SystemExit) as e:
        parse_config()

    assert e.type is SystemExit
    assert e.value.code == 2
