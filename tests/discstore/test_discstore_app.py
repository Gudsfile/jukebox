import sys
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
    UiCommand,
)


def assert_app_mocks_calls(app_mocks, expected_calls: dict):
    all_mock_names = [
        "parse_config",
        "set_logger",
        "build_api_app",
        "build_interactive",
        "build_cli",
        "build_ui_app",
    ]

    for name in all_mock_names:
        mock_obj = getattr(app_mocks, name)
        if name in expected_calls:
            expected_args = expected_calls[name]
            mock_obj.assert_called_once_with(*expected_args)
        else:
            mock_obj.assert_not_called()


@pytest.fixture
def app_mocks(mocker):
    class Mocks:
        parse_config = mocker.patch("discstore.app.parse_config")
        set_logger = mocker.patch("discstore.app.set_logger")
        build_api_app = mocker.patch("discstore.app.build_api_app")
        build_interactive = mocker.patch("discstore.app.build_interactive_cli_controller")
        build_cli = mocker.patch("discstore.app.build_cli_controller")
        build_ui_app = mocker.patch("discstore.app.build_ui_app")

    return Mocks()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="uvicorn requires Python 3.8+")
@pytest.mark.parametrize(
    "command, expected_builder",
    [
        (ApiCommand(type="api", port=1234), "build_api_app"),
        (UiCommand(type="ui", port=1234), "build_ui_app"),
    ],
)
def test_main_starts_api(mocker, app_mocks, command, expected_builder):
    mock_uvicorn = mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})["uvicorn"]
    config = CLIConfig(library="fake_library_path", verbose=True, command=command)
    app_mocks.parse_config.return_value = config
    fake_apps = {
        "build_api_app": MagicMock(),
        "build_ui_app": MagicMock(),
    }
    app_mocks.build_api_app.return_value = MagicMock(app=fake_apps["build_api_app"])
    app_mocks.build_ui_app.return_value = MagicMock(app=fake_apps["build_ui_app"])

    app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": (True,),
            expected_builder: ("fake_library_path",),
        },
    )
    mock_uvicorn.run.assert_called_once_with(fake_apps[expected_builder], host="0.0.0.0", port=1234)


def test_main_starts_interactive_cli(app_mocks):
    config = CLIConfig(library="fake_library_path", verbose=True, command=InteractiveCliCommand(type="interactive"))
    app_mocks.parse_config.return_value = config
    mock_interactive_cli = MagicMock()
    app_mocks.build_interactive.return_value = mock_interactive_cli

    app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": (True,),
            "build_interactive": ("fake_library_path",),
        },
    )
    mock_interactive_cli.run.assert_called_once()


@pytest.mark.parametrize(
    "cli_command",
    [
        CliAddCommand(type="add", tag="dummy_tag", uri="dummy_uri"),
        CliRemoveCommand(type="remove", tag="dummy_tag"),
        CliListCommand(type="list", mode=CliListCommandModes.table),
        CliEditCommand(type="edit", tag="dummy_tag", uri="dummy_uri"),
    ],
)
def test_main_starts_standard_cli(app_mocks, cli_command):
    config = CLIConfig(library="fake_library_path", verbose=True, command=cli_command)
    app_mocks.parse_config.return_value = config
    mock_standard_cli = MagicMock()
    app_mocks.build_cli.return_value = mock_standard_cli

    app.main()

    assert_app_mocks_calls(
        app_mocks,
        {
            "parse_config": (),
            "set_logger": (True,),
            "build_cli": ("fake_library_path",),
        },
    )
    mock_standard_cli.run.assert_called_once_with(cli_command)
