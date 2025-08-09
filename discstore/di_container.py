from discstore.adapters.inbound.cli_controller import CLIController
from discstore.adapters.inbound.interactive_cli_controller import InteractiveCLIController
from discstore.adapters.outbound.json_library_repository import JsonLibraryRepository
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


def build_cli_controller(library_path: str):
    repository = JsonLibraryRepository(library_path)
    return CLIController(
        AddDisc(repository),
        ListDiscs(repository),
    )


def build_interactive_cli_controller(library_path: str):
    repository = JsonLibraryRepository(library_path)
    return InteractiveCLIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
    )


def build_api_app(library_path: str):
    repository = JsonLibraryRepository(library_path)
    from discstore.adapters.inbound.api_controller import APIController
    from discstore.adapters.inbound.api_controller import app as fastapi_app

    APIController(
        AddDisc(repository),
        ListDiscs(repository),
        RemoveDisc(repository),
    )
    return fastapi_app
