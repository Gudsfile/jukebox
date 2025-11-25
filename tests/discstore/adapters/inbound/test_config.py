import pytest

from discstore.adapters.inbound.config import (
    DEFAULT_LIBRARY_PATH,
    ApiCommand,
    CliAddCommand,
    CliEditCommand,
    CliListCommand,
    CliRemoveCommand,
    InteractiveCliCommand,
    parse_config,
)


def test_parse_add_command(mocker):
    argv = [
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
    ]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert config.verbose is False
    assert isinstance(config.command, CliAddCommand)
    assert config.command.type == "add"
    assert config.command.tag == "my-tag"
    assert config.command.uri == "/path/to/media.mp3"
    assert config.command.track == "My Song"
    assert config.command.artist == "The Testers"
    assert config.command.album == "Code Hits"


def test_parse_list_command(mocker):
    argv = ["prog_name", "list", "line"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert isinstance(config.command, CliListCommand)
    assert config.command.type == "list"
    assert config.command.mode == "line"


def test_parse_remove_command(mocker):
    argv = ["prog_name", "remove", "tag-to-delete"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert isinstance(config.command, CliRemoveCommand)
    assert config.command.type == "remove"
    assert config.command.tag == "tag-to-delete"


def test_parse_edit_command(mocker):
    argv = [
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
    ]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert config.verbose is False
    assert isinstance(config.command, CliEditCommand)
    assert config.command.type == "edit"
    assert config.command.tag == "my-tag"
    assert config.command.uri == "/path/to/media.mp3"
    assert config.command.track == "My Song"
    assert config.command.artist == "The Testers"
    assert config.command.album == "Code Hits"


def test_parse_api_command_with_port(mocker):
    argv = ["prog_name", "api", "--port", "9999"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert isinstance(config.command, ApiCommand)
    assert config.command.type == "api"
    assert config.command.port == 9999


def test_parse_interactive_command(mocker):
    argv = ["prog_name", "interactive"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert isinstance(config.command, InteractiveCliCommand)
    assert config.command.type == "interactive"


def test_verbose_and_library_flags(mocker):
    argv = ["prog_name", "-v", "--library", "/custom/path.json", "list", "table"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert config.verbose is True
    assert config.library == "/custom/path.json"


def test_library_path_from_env_var(mocker):
    mocker.patch.dict("os.environ", {"JUKEBOX_LIBRARY_PATH": "/env/path.json"})
    argv = ["prog_name", "list", "table"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert config.library == "/env/path.json"


def test_default_library_path(mocker):
    mocker.patch.dict("os.environ", {}, clear=True)
    argv = ["prog_name", "list", "table"]
    mocker.patch("sys.argv", argv)

    config = parse_config()

    assert config.library == DEFAULT_LIBRARY_PATH


def test_validation_error_exits(mocker):
    argv = ["prog_name", "add", "a-tag-without-a-uri"]
    mocker.patch("sys.argv", argv)

    with pytest.raises(SystemExit) as e:
        parse_config()

    assert e.type is SystemExit
    assert e.value.code == 2
