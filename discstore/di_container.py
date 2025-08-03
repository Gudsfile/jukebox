from discstore.adapters.inbound.cli_controller import CLIController
from discstore.adapters.outbound.json_library_repository import JsonLibraryRepository
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs


def build_cli_controller(filepath: str) -> CLIController:
    repository = JsonLibraryRepository(filepath)
    return CLIController(
        AddDisc(repository),
        ListDiscs(repository),
    )


def build_api_app(filepath: str):
    repository = JsonLibraryRepository(filepath)
    from discstore.adapters.inbound.api_controller import APIController
    from discstore.adapters.inbound.api_controller import app as fastapi_app

    APIController(
        AddDisc(repository),
        ListDiscs(repository),
    )
    return fastapi_app
