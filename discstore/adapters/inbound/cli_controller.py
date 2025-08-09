from typing import Union

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.adapters.inbound.config import CliAddCommand, CliListCommand
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs


class CLIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs):
        self.add_disc = add_disc
        self.list_discs = list_discs

    def run(self, command: Union[CliAddCommand, CliListCommand]) -> None:
        if isinstance(command, CliAddCommand):
            self.add_discs_flow(command)
        elif isinstance(command, CliListCommand):
            self.list_discs_flow(command)

    def add_discs_flow(self, command: CliAddCommand) -> None:
        tag = command.tag
        uri = command.uri
        option = DiscOption()
        metadata = DiscMetadata(**command.model_dump())

        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        print("✅ CD ajouté avec succès.")

    def list_discs_flow(self, command) -> None:
        discs = self.list_discs.execute()
        if command.mode == "table":
            display_library_table(discs)
            return
        if command.mode == "line":
            display_library_line(discs)
            return
        print(f"Displaying mode not implemented yet: {command.mode}")
