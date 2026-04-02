from unittest.mock import MagicMock

import pytest

from discstore.di_container import build_cli_controller, build_interactive_cli_controller
from jukebox.shared.config_utils import get_current_tag_path


@pytest.fixture
def mocks(mocker):
    class Mocks:
        repo_class: MagicMock = mocker.patch("discstore.di_container.JsonLibraryAdapter")
        current_tag_repo_class: MagicMock = mocker.patch("discstore.di_container.TextCurrentTagAdapter")
        add_disc_class: MagicMock = mocker.patch("discstore.di_container.AddDisc")
        list_discs_class: MagicMock = mocker.patch("discstore.di_container.ListDiscs")
        remove_disc_class: MagicMock = mocker.patch("discstore.di_container.RemoveDisc")
        edit_disc_class: MagicMock = mocker.patch("discstore.di_container.EditDisc")
        get_disc_class: MagicMock = mocker.patch("discstore.di_container.GetDisc")
        get_current_tag_status_class: MagicMock = mocker.patch("discstore.di_container.GetCurrentTagStatus")
        resolve_tag_id_class: MagicMock = mocker.patch("discstore.di_container.ResolveTagId")
        search_discs_class: MagicMock = mocker.patch("discstore.di_container.SearchDiscs")
        repo_instance: MagicMock = MagicMock()
        current_tag_repo_instance: MagicMock = MagicMock()
        add_disc_instance: MagicMock = MagicMock()
        list_discs_instance: MagicMock = MagicMock()
        remove_disc_instance: MagicMock = MagicMock()
        edit_disc_instance: MagicMock = MagicMock()
        get_disc_instance: MagicMock = MagicMock()
        get_current_tag_status_instance: MagicMock = MagicMock()
        resolve_tag_id_instance: MagicMock = MagicMock()
        search_discs_instance: MagicMock = MagicMock()

    mocks = Mocks()

    mocks.repo_class.return_value = mocks.repo_instance
    mocks.current_tag_repo_class.return_value = mocks.current_tag_repo_instance
    mocks.add_disc_class.return_value = mocks.add_disc_instance
    mocks.list_discs_class.return_value = mocks.list_discs_instance
    mocks.remove_disc_class.return_value = mocks.remove_disc_instance
    mocks.edit_disc_class.return_value = mocks.edit_disc_instance
    mocks.get_disc_class.return_value = mocks.get_disc_instance
    mocks.get_current_tag_status_class.return_value = mocks.get_current_tag_status_instance
    mocks.resolve_tag_id_class.return_value = mocks.resolve_tag_id_instance
    mocks.search_discs_class.return_value = mocks.search_discs_instance

    return mocks


def test_get_current_tag_path_derives_path_beside_library(tmp_path):
    library_path = tmp_path / "nested" / "library.json"

    assert get_current_tag_path(str(library_path)) == str(tmp_path / "nested" / "current-tag.txt")


def test_build_cli_controller_wiring(mocker, mocks):
    mock_cli_controller_instance = MagicMock()
    mock_cli_controller_class = mocker.patch(
        "discstore.di_container.CLIController", return_value=mock_cli_controller_instance
    )

    result = build_cli_controller("/test/library.json")

    mocks.repo_class.assert_called_once_with("/test/library.json")
    mocks.current_tag_repo_class.assert_called_once_with("/test/current-tag.txt")
    mocks.add_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.list_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.remove_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.edit_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.get_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.search_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.get_current_tag_status_class.assert_called_once_with(mocks.current_tag_repo_instance, mocks.repo_instance)
    mocks.resolve_tag_id_class.assert_called_once_with(mocks.get_current_tag_status_instance)
    mock_cli_controller_class.assert_called_once_with(
        mocks.add_disc_instance,
        mocks.list_discs_instance,
        mocks.remove_disc_instance,
        mocks.edit_disc_instance,
        mocks.get_disc_instance,
        mocks.search_discs_instance,
        mocks.resolve_tag_id_instance,
    )
    assert result is mock_cli_controller_instance


def test_build_interactive_cli_controller_wiring(mocker, mocks):
    mock_interactive_cli_instance = MagicMock()
    mock_interactive_cli_class = mocker.patch(
        "discstore.di_container.InteractiveCLIController", return_value=mock_interactive_cli_instance
    )

    result = build_interactive_cli_controller("/test/library.json")

    mocks.repo_class.assert_called_once_with("/test/library.json")
    mocks.current_tag_repo_class.assert_called_once_with("/test/current-tag.txt")
    mocks.add_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.list_discs_class.assert_called_once_with(mocks.repo_instance)
    mocks.remove_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.edit_disc_class.assert_called_once_with(mocks.repo_instance)
    mocks.get_current_tag_status_class.assert_called_once_with(mocks.current_tag_repo_instance, mocks.repo_instance)
    mock_interactive_cli_class.assert_called_once_with(
        mocks.add_disc_instance,
        mocks.list_discs_instance,
        mocks.remove_disc_instance,
        mocks.edit_disc_instance,
        mocks.get_current_tag_status_instance,
    )
    assert result is mock_interactive_cli_instance
