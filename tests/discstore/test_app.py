from unittest.mock import MagicMock

import pytest

from discstore import app
from discstore.adapters.inbound.config import (
    ApiCommand,
    CliAddCommand,
    CLIConfig,
    CliEditCommand,
    CliListCommand,
    CliListCommandModes,
    CliRemoveCommand,
    InteractiveCliCommand,
)


def test_main_starts_api(mocker):
    mock_uvicorn = MagicMock()
    mocker.patch.dict("sys.modules", {"uvicorn": mock_uvicorn})

    mock_parse_config = mocker.patch("discstore.app.parse_config")
    mock_set_logger = mocker.patch("discstore.app.set_logger")
    mock_build_api_app = mocker.patch("discstore.app.build_api_app")
    mock_build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
    mock_build_cli = mocker.patch("discstore.app.build_cli_controller")

    config = CLIConfig(library="fake_library_path", verbose=True, command=ApiCommand(type="api", port=1234))

    mock_parse_config.return_value = config

    fake_app = MagicMock()
    mock_build_api_app.return_value = fake_app

    app.main()

    mock_parse_config.assert_called_once()
    mock_set_logger.assert_called_once_with(True)
    mock_build_api_app.assert_called_once_with("fake_library_path")
    mock_uvicorn.run.assert_called_once_with(fake_app, host="0.0.0.0", port=1234)

    mock_build_interactive.assert_not_called()
    mock_build_cli.assert_not_called()


def test_main_starts_interactive_cli(mocker):
    mock_parse_config = mocker.patch("discstore.app.parse_config")
    mock_set_logger = mocker.patch("discstore.app.set_logger")
    mock_build_api_app = mocker.patch("discstore.app.build_api_app")
    mock_build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
    mock_build_cli = mocker.patch("discstore.app.build_cli_controller")

    config = CLIConfig(library="fake_library_path", verbose=True, command=InteractiveCliCommand(type="interactive"))

    mock_parse_config.return_value = config

    mock_interactive_cli = MagicMock()
    mock_build_interactive.return_value = mock_interactive_cli

    app.main()

    mock_parse_config.assert_called_once()
    mock_set_logger.assert_called_once_with(True)
    mock_build_interactive.assert_called_once_with("fake_library_path")
    mock_interactive_cli.run.assert_called_once()

    mock_build_api_app.assert_not_called()
    mock_build_cli.assert_not_called()


@pytest.mark.parametrize(
    "cli_command",
    [
        (CliAddCommand(type="add", tag="dummy_tag", uri="dummy_uri")),
        (CliRemoveCommand(type="remove", tag="dummy_tag")),
        (CliListCommand(type="list", mode=CliListCommandModes.table)),
        (CliEditCommand(type="edit", tag="dummy_tag", uri="dummy_uri")),
    ],
)
def test_main_starts_standard_cli(mocker, cli_command):
    mock_parse_config = mocker.patch("discstore.app.parse_config")
    mock_set_logger = mocker.patch("discstore.app.set_logger")
    mock_build_api_app = mocker.patch("discstore.app.build_api_app")
    mock_build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
    mock_build_cli = mocker.patch("discstore.app.build_cli_controller")

    config = CLIConfig(library="fake_library_path", verbose=True, command=cli_command)

    mock_parse_config.return_value = config

    mock_standard_cli = MagicMock()
    mock_build_cli.return_value = mock_standard_cli

    app.main()

    mock_parse_config.assert_called_once()
    mock_set_logger.assert_called_once_with(True)
    mock_build_cli.assert_called_once_with("fake_library_path")
    mock_standard_cli.run.assert_called_once_with(cli_command)

    mock_build_api_app.assert_not_called()
    mock_build_interactive.assert_not_called()
