from typing import Callable, Optional

from discstore.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from discstore.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService as SettingsServiceImpl
from jukebox.settings.resolve import build_environment_settings_overrides
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.config_utils import get_current_tag_path
from jukebox.sonos.service import DefaultSonosService, SonosService

from .commands import ApiCommand, UiCommand
from .services import AdminServices


def build_settings_service(
    library: Optional[str],
    command: Optional[object],
    logger_warning: Callable[[str], None],
    sonos_service: Optional[SonosService] = None,
) -> SettingsService:
    cli_overrides = {}

    if library is not None:
        cli_overrides.setdefault("paths", {})["library_path"] = library

    if isinstance(command, ApiCommand) and command.port is not None:
        cli_overrides.setdefault("admin", {}).setdefault("api", {})["port"] = command.port

    if isinstance(command, UiCommand) and command.port is not None:
        cli_overrides.setdefault("admin", {}).setdefault("ui", {})["port"] = command.port

    return SettingsServiceImpl(
        repository=FileSettingsRepository(),
        env_overrides=build_environment_settings_overrides(logger_warning),
        cli_overrides=cli_overrides,
        sonos_service=sonos_service,
    )


def build_admin_services(
    library: Optional[str],
    command: Optional[object],
    logger_warning: Callable[[str], None],
) -> AdminServices:
    sonos_service = build_sonos_service()
    settings_service = build_settings_service(
        library=library,
        command=command,
        logger_warning=logger_warning,
        sonos_service=sonos_service,
    )
    return AdminServices(settings=settings_service, sonos=sonos_service)


def build_admin_api_app(library_path: str, services: AdminServices):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))

    from discstore.adapters.inbound.api_controller import APIController

    return APIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
        services.settings,
        services.sonos,
    )


def build_admin_ui_app(library_path: str, services: AdminServices):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))

    from discstore.adapters.inbound.ui_controller import UIController

    return UIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
        services.settings,
    )


def build_sonos_service() -> SonosService:
    return DefaultSonosService(SoCoSonosDiscoveryAdapter())
