from unittest.mock import patch

import pytest

from discstore.adapters.inbound.config import (
    ApiCommand,
    CliAddCommand,
    CliEditCommand,
    CliGetCommand,
    CliListCommand,
    CliRemoveCommand,
    InteractiveCliCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    UiCommand,
    parse_config,
)


@patch(
    "sys.argv",
    [
        "prog_name",
        "add",
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
def test_parse_add_command():
    config = parse_config()

    assert config.verbose is False
    assert isinstance(config.command, CliAddCommand)
    assert config.command.type == "add"
    assert config.command.tag == "my-tag"
    assert config.command.use_current_tag is False
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
    assert config.command.use_current_tag is False


@patch("sys.argv", ["prog_name", "remove", "--from-current"])
def test_parse_remove_command_with_from_current():
    config = parse_config()

    assert isinstance(config.command, CliRemoveCommand)
    assert config.command.type == "remove"
    assert config.command.tag is None
    assert config.command.use_current_tag is True


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

    assert isinstance(config.command, CliEditCommand)
    assert config.command.type == "edit"
    assert config.command.tag == "my-tag"
    assert config.command.uri == "/path/to/media.mp3"


@patch("sys.argv", ["prog_name", "get", "--from-current"])
def test_parse_get_command_with_from_current():
    config = parse_config()

    assert isinstance(config.command, CliGetCommand)
    assert config.command.use_current_tag is True


@patch("sys.argv", ["prog_name", "remove", "tag-to-delete", "--from-current"])
def test_tag_source_validation_error_exits():
    with pytest.raises(SystemExit) as err:
        parse_config()

    assert err.value.code == 1


@patch("sys.argv", ["prog_name", "api", "--port", "9999"])
def test_parse_api_command_with_port():
    config = parse_config()

    assert isinstance(config.command, ApiCommand)
    assert config.command.port == 9999


@patch("sys.argv", ["prog_name", "ui", "--port", "9999"])
def test_parse_ui_command_with_port():
    config = parse_config()

    assert isinstance(config.command, UiCommand)
    assert config.command.port == 9999


@patch("sys.argv", ["prog_name", "interactive"])
def test_parse_interactive_command():
    config = parse_config()

    assert isinstance(config.command, InteractiveCliCommand)


@patch("sys.argv", ["prog_name", "settings", "show"])
def test_parse_settings_show_command():
    config = parse_config()

    assert isinstance(config.command, SettingsShowCommand)
    assert config.command.effective is False
    assert config.command.json_output is False


@patch("sys.argv", ["prog_name", "settings", "show", "--effective"])
def test_parse_settings_show_effective_command():
    config = parse_config()

    assert isinstance(config.command, SettingsShowCommand)
    assert config.command.effective is True
    assert config.command.json_output is False


@patch("sys.argv", ["prog_name", "settings", "show", "--json"])
def test_parse_settings_show_json_command():
    config = parse_config()

    assert isinstance(config.command, SettingsShowCommand)
    assert config.command.effective is False
    assert config.command.json_output is True


@patch("sys.argv", ["prog_name", "settings", "set", "admin.api.port", "9000"])
def test_parse_settings_set_command():
    config = parse_config()

    assert isinstance(config.command, SettingsSetCommand)
    assert config.command.dotted_path == "admin.api.port"
    assert config.command.value == "9000"
    assert config.command.json_output is False


@patch("sys.argv", ["prog_name", "settings", "set", "admin.api.port", "9000", "--json"])
def test_parse_settings_set_json_command():
    config = parse_config()

    assert isinstance(config.command, SettingsSetCommand)
    assert config.command.dotted_path == "admin.api.port"
    assert config.command.value == "9000"
    assert config.command.json_output is True


@patch("sys.argv", ["prog_name", "settings", "reset", "admin.ui.port"])
def test_parse_settings_reset_command():
    config = parse_config()

    assert isinstance(config.command, SettingsResetCommand)
    assert config.command.dotted_path == "admin.ui.port"
    assert config.command.json_output is False


@patch("sys.argv", ["prog_name", "settings", "reset", "admin.ui.port", "--json"])
def test_parse_settings_reset_json_command():
    config = parse_config()

    assert isinstance(config.command, SettingsResetCommand)
    assert config.command.dotted_path == "admin.ui.port"
    assert config.command.json_output is True


@patch("sys.argv", ["prog_name", "settings", "reset", "admin"])
def test_parse_settings_reset_section_command():
    config = parse_config()

    assert isinstance(config.command, SettingsResetCommand)
    assert config.command.dotted_path == "admin"


@patch("sys.argv", ["prog_name", "-v", "--library", "/custom/path.json", "list", "table"])
def test_verbose_and_library_flags():
    config = parse_config()

    assert config.verbose is True
    assert config.library == "/custom/path.json"


@patch("sys.argv", ["prog_name", "list", "table"])
def test_default_library_override_is_none():
    config = parse_config()

    assert config.library is None


@patch("sys.argv", ["prog_name", "add", "a-tag-without-a-uri"])
def test_add_without_required_uri_exits():
    with pytest.raises(SystemExit) as err:
        parse_config()

    assert err.value.code == 2
