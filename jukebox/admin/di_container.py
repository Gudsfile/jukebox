from typing import cast

from jukebox.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter
from jukebox.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter
from jukebox.domain.use_cases.library.add_disc import AddDisc
from jukebox.domain.use_cases.library.edit_disc import EditDisc
from jukebox.domain.use_cases.library.get_current_tag_status import GetCurrentTagStatus
from jukebox.domain.use_cases.library.get_disc import GetDisc
from jukebox.domain.use_cases.library.list_discs import ListDiscs
from jukebox.domain.use_cases.library.remove_disc import RemoveDisc
from jukebox.domain.use_cases.library.resolve_tag_id import ResolveTagId
from jukebox.domain.use_cases.library.search_discs import SearchDiscs
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService as SettingsServiceImpl
from jukebox.settings.resolve import build_environment_settings_overrides
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject
from jukebox.shared.config_utils import get_current_tag_path
from jukebox.sonos.service import DefaultSonosService, SonosService

from .commands import ApiCommand, UiCommand
from .services import AdminServices


def build_settings_service(
    library: str | None,
    command: object | None,
) -> SettingsService:
    cli_overrides: JsonObject = {}

    if library is not None:
        cast(JsonObject, cli_overrides.setdefault("paths", {}))["library_path"] = library

    if isinstance(command, ApiCommand) and command.port is not None:
        admin = cast(JsonObject, cli_overrides.setdefault("admin", {}))
        cast(JsonObject, admin.setdefault("api", {}))["port"] = command.port

    if isinstance(command, UiCommand) and command.port is not None:
        admin = cast(JsonObject, cli_overrides.setdefault("admin", {}))
        cast(JsonObject, admin.setdefault("ui", {}))["port"] = command.port

    return SettingsServiceImpl(
        repository=FileSettingsRepository(),
        env_overrides=build_environment_settings_overrides(),
        cli_overrides=cli_overrides,
    )


def build_admin_services(
    library: str | None,
    command: object | None,
) -> AdminServices:
    sonos_service = build_sonos_service()
    settings_service = build_settings_service(
        library=library,
        command=command,
    )
    return AdminServices(settings=settings_service, sonos=sonos_service)


def build_admin_api_app(library_path: str, services: AdminServices):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))

    from jukebox.adapters.inbound.admin.api_controller import APIController

    return APIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
        services.settings,
        services.sonos,
    )


def build_admin_ui_app(library_path: str, services: AdminServices):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))

    from jukebox.adapters.inbound.admin.ui_controller import UIController

    return UIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
        services.settings,
        services.sonos,
    )


def build_sonos_service() -> SonosService:
    return DefaultSonosService(SoCoSonosDiscoveryAdapter())


def build_cli_controller(library_path: str):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))
    get_current_tag_status = GetCurrentTagStatus(current_tag_repository, repository)

    from jukebox.adapters.inbound.admin.cli_controller import CLIController

    return CLIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetDisc(repository),
        SearchDiscs(repository),
        ResolveTagId(get_current_tag_status),
    )


def build_interactive_cli_controller(library_path: str):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(get_current_tag_path(library_path))

    from jukebox.adapters.inbound.admin.interactive_cli_controller import InteractiveCLIController

    return InteractiveCLIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
    )
