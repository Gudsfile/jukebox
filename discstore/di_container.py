from discstore.adapters.inbound.cli_controller import CLIController
from discstore.adapters.inbound.interactive_cli_controller import (
    InteractiveCLIController,
)
from discstore.adapters.outbound.json_library_adapter import JsonLibraryAdapter
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from discstore.domain.use_cases.resolve_tag_id import ResolveTagId
from discstore.domain.use_cases.search_discs import SearchDiscs
from jukebox.adapters.outbound.text_current_tag_adapter import TextCurrentTagAdapter


def build_cli_controller(library_path: str):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(library_path)
    get_current_tag_status = GetCurrentTagStatus(current_tag_repository, repository)
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
    current_tag_repository = TextCurrentTagAdapter(library_path)
    return InteractiveCLIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
    )


def build_api_app(library_path: str):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(library_path)
    from discstore.adapters.inbound.api_controller import APIController

    api_controller = APIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
    )
    return api_controller


def build_ui_app(library_path: str):
    repository = JsonLibraryAdapter(library_path)
    current_tag_repository = TextCurrentTagAdapter(library_path)
    from discstore.adapters.inbound.ui_controller import UIController

    ui_controller = UIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
        EditDisc(repository),
        GetDisc(repository),
        GetCurrentTagStatus(current_tag_repository, repository),
    )
    return ui_controller
