from unittest.mock import MagicMock

import pytest

from jukebox.admin.commands import ApiCommand, SettingsShowCommand, UiCommand
from jukebox.admin.di_container import (
    build_admin_api_app,
    build_admin_services,
    build_admin_ui_app,
    build_settings_service,
)
from jukebox.admin.services import AdminServices
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService as SettingsServiceImpl


@pytest.mark.parametrize(
    ("command", "expected_overrides"),
    [
        (
            ApiCommand(type="api", port=9100),
            {"paths": {"library_path": "/custom/library.json"}, "admin": {"api": {"port": 9100}}},
        ),
        (
            UiCommand(type="ui", port=9200),
            {"paths": {"library_path": "/custom/library.json"}, "admin": {"ui": {"port": 9200}}},
        ),
        (
            SettingsShowCommand(type="settings_show"),
            {"paths": {"library_path": "/custom/library.json"}},
        ),
    ],
)
def test_build_settings_service_maps_cli_overrides(command, expected_overrides):
    service = build_settings_service(
        library="/custom/library.json",
        command=command,
    )

    assert isinstance(service, SettingsServiceImpl)
    assert isinstance(service.repository, FileSettingsRepository)
    assert service.cli_overrides == expected_overrides


def test_build_admin_services_builds_peer_settings_and_sonos_services(mocker):
    build_sonos_service = mocker.patch("jukebox.admin.di_container.build_sonos_service")
    sonos_service = MagicMock()
    build_sonos_service.return_value = sonos_service

    services = build_admin_services(
        library="/custom/library.json",
        command=SettingsShowCommand(type="settings_show"),
    )

    assert isinstance(services, AdminServices)
    assert services.sonos is sonos_service
    assert isinstance(services.settings, SettingsServiceImpl)


def test_build_admin_services_shares_one_settings_path_with_the_settings_repository(mocker):
    mocker.patch("jukebox.admin.di_container.build_sonos_service")
    mocker.patch("jukebox.admin.di_container.default_settings_path", return_value="/config/jukebox/settings.json")

    services = build_admin_services(
        library="/custom/library.json",
        command=SettingsShowCommand(type="settings_show"),
    )

    assert services.settings_path == "/config/jukebox/settings.json"
    assert isinstance(services.settings, SettingsServiceImpl)
    assert isinstance(services.settings.repository, FileSettingsRepository)
    assert services.settings.repository.filepath == services.settings_path


@pytest.fixture
def bootstrap_mocks(mocker):
    class Mocks:
        repo_class = mocker.patch("jukebox.admin.di_container.JsonLibraryAdapter")
        current_tag_repo_class = mocker.patch("jukebox.admin.di_container.TextCurrentTagAdapter")
        add_disc_class = mocker.patch("jukebox.admin.di_container.AddDisc")
        list_discs_class = mocker.patch("jukebox.admin.di_container.ListDiscs")
        remove_disc_class = mocker.patch("jukebox.admin.di_container.RemoveDisc")
        edit_disc_class = mocker.patch("jukebox.admin.di_container.EditDisc")
        get_disc_class = mocker.patch("jukebox.admin.di_container.GetDisc")
        get_current_tag_status_class = mocker.patch("jukebox.admin.di_container.GetCurrentTagStatus")
        preview_library_import_class = mocker.patch("jukebox.admin.di_container.PreviewLibraryImport")
        import_library_class = mocker.patch("jukebox.admin.di_container.ImportLibrary")
        repo_instance = MagicMock()
        current_tag_repo_instance = MagicMock()
        add_disc_instance = MagicMock()
        list_disc_instance = MagicMock()
        remove_disc_instance = MagicMock()
        edit_disc_instance = MagicMock()
        get_disc_instance = MagicMock()
        get_current_tag_status_instance = MagicMock()
        preview_library_import_instance = MagicMock()
        import_library_instance = MagicMock()

    mocks = Mocks()
    mocks.repo_class.return_value = mocks.repo_instance
    mocks.current_tag_repo_class.return_value = mocks.current_tag_repo_instance
    mocks.add_disc_class.return_value = mocks.add_disc_instance
    mocks.list_discs_class.return_value = mocks.list_disc_instance
    mocks.remove_disc_class.return_value = mocks.remove_disc_instance
    mocks.edit_disc_class.return_value = mocks.edit_disc_instance
    mocks.get_disc_class.return_value = mocks.get_disc_instance
    mocks.get_current_tag_status_class.return_value = mocks.get_current_tag_status_instance
    mocks.preview_library_import_class.return_value = mocks.preview_library_import_instance
    mocks.import_library_class.return_value = mocks.import_library_instance
    return mocks


def test_build_admin_api_app_wiring(mocker, bootstrap_mocks):
    mock_api_instance = MagicMock()
    mock_api_controller_class = MagicMock(return_value=mock_api_instance)
    mocker.patch.dict(
        "sys.modules",
        {"jukebox.adapters.inbound.admin.api_controller": MagicMock(APIController=mock_api_controller_class)},
    )
    services = AdminServices(settings=MagicMock(), sonos=MagicMock(), settings_path="/test/settings.json")

    result = build_admin_api_app("/test/library.json", services)

    bootstrap_mocks.repo_class.assert_called_once_with("/test/library.json")
    bootstrap_mocks.current_tag_repo_class.assert_called_once_with("/test/current-tag.txt")
    mock_api_controller_class.assert_called_once_with(
        bootstrap_mocks.add_disc_instance,
        bootstrap_mocks.list_disc_instance,
        bootstrap_mocks.remove_disc_instance,
        bootstrap_mocks.edit_disc_instance,
        bootstrap_mocks.get_disc_instance,
        bootstrap_mocks.get_current_tag_status_instance,
        services.settings,
        services.sonos,
        library_path="/test/library.json",
        settings_path="/test/settings.json",
        preview_library_import=bootstrap_mocks.preview_library_import_instance,
        import_library=bootstrap_mocks.import_library_instance,
    )
    bootstrap_mocks.preview_library_import_class.assert_called_once_with(bootstrap_mocks.repo_instance)
    bootstrap_mocks.import_library_class.assert_called_once_with(bootstrap_mocks.repo_instance)
    assert result is mock_api_instance


def test_build_admin_ui_app_wiring(mocker, bootstrap_mocks):
    mock_ui_instance = MagicMock()
    mock_ui_controller_class = MagicMock(return_value=mock_ui_instance)
    mocker.patch.dict(
        "sys.modules",
        {"jukebox.adapters.inbound.admin.ui_controller": MagicMock(UIController=mock_ui_controller_class)},
    )
    services = AdminServices(settings=MagicMock(), sonos=MagicMock(), settings_path="/test/settings.json")

    result = build_admin_ui_app("/test/library.json", services)

    bootstrap_mocks.repo_class.assert_called_once_with("/test/library.json")
    bootstrap_mocks.current_tag_repo_class.assert_called_once_with("/test/current-tag.txt")
    mock_ui_controller_class.assert_called_once_with(
        bootstrap_mocks.add_disc_instance,
        bootstrap_mocks.list_disc_instance,
        bootstrap_mocks.remove_disc_instance,
        bootstrap_mocks.edit_disc_instance,
        bootstrap_mocks.get_disc_instance,
        bootstrap_mocks.get_current_tag_status_instance,
        services.settings,
        services.sonos,
        library_path="/test/library.json",
        settings_path="/test/settings.json",
        preview_library_import=bootstrap_mocks.preview_library_import_instance,
        import_library=bootstrap_mocks.import_library_instance,
    )
    bootstrap_mocks.preview_library_import_class.assert_called_once_with(bootstrap_mocks.repo_instance)
    bootstrap_mocks.import_library_class.assert_called_once_with(bootstrap_mocks.repo_instance)
    assert result is mock_ui_instance
