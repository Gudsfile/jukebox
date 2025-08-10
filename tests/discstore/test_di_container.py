from unittest.mock import MagicMock

import pytest

from discstore.di_container import (
    build_api_app,
    build_cli_controller,
    build_interactive_cli_controller,
)


@pytest.fixture
def mocks(mocker):
    class Mocks:
        repo_class: MagicMock = mocker.patch("discstore.di_container.JsonLibraryRepository")
        add_disc_class: MagicMock = mocker.patch("discstore.di_container.AddDisc")
        list_discs_class: MagicMock = mocker.patch("discstore.di_container.ListDiscs")
        remove_disc_class: MagicMock = mocker.patch("discstore.di_container.RemoveDisc")
        repo_instance: MagicMock = MagicMock()
        add_disc_instance: MagicMock = MagicMock()
        list_discs_instance: MagicMock = MagicMock()
        remove_disc_instance: MagicMock = MagicMock()

    mocks = Mocks()

    mocks.repo_class.return_value = mocks.repo_instance
    mocks.add_disc_class.return_value = mocks.add_disc_instance
    mocks.list_discs_class.return_value = mocks.list_discs_instance
    mocks.remove_disc_class.return_value = mocks.remove_disc_instance

    return mocks


def test_build_cli_controller_wiring(mocker, mocks):
    mock_cli_controller_instance = MagicMock()
    mock_cli_controller_class = mocker.patch(
        "discstore.di_container.CLIController", return_value=mock_cli_controller_instance
    )

    result = build_cli_controller("fake_library_path")

    mocks.repo_class.assert_called_once_with("fake_library_path")
    mocks.add_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.list_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.remove_disc_class.assert_called_once_with(mocks.repo_instance)
    mock_cli_controller_class.assert_called_once_with(
        mocks.add_disc_instance,
        mocks.list_discs_instance,
        mocks.remove_disc_instance,
    )
    assert result is mock_cli_controller_instance


def test_build_interactive_cli_controller_wiring(mocker, mocks):
    mock_interactive_cli_instance = MagicMock()
    mock_interactive_cli_class = mocker.patch(
        "discstore.di_container.InteractiveCLIController", return_value=mock_interactive_cli_instance
    )

    result = build_interactive_cli_controller("fake_library_path")

    mocks.repo_class.assert_called_once_with("fake_library_path")
    mocks.add_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.list_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.remove_disc_class.assert_called_once_with(mocks.repo_instance)
    mock_interactive_cli_class.assert_called_once_with(
        mocks.add_disc_instance, mocks.list_discs_instance, mocks.remove_disc_instance
    )
    assert result is mock_interactive_cli_instance


def test_build_api_app_wiring(mocker, mocks):
    mock_api_controller_module = MagicMock()
    mock_api_controller_class = MagicMock()
    mock_fastapi_app_instance = MagicMock()
    mock_api_controller_module.APIController = mock_api_controller_class
    mock_api_controller_module.app = mock_fastapi_app_instance
    mocker.patch.dict("sys.modules", {"discstore.adapters.inbound.api_controller": mock_api_controller_module})

    result = build_api_app("fake_library_path")

    mocks.repo_class.assert_called_once_with("fake_library_path")
    mocks.add_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.list_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.remove_disc_class.assert_called_once_with(mocks.repo_instance)
    mock_api_controller_class.assert_called_once_with(
        mocks.add_disc_instance, mocks.list_discs_instance, mocks.remove_disc_instance
    )
    assert result is mock_fastapi_app_instance
