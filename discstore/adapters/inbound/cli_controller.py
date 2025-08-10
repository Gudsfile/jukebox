import logging
from typing import Union

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.adapters.inbound.config import CliAddCommand, CliEditCommand, CliListCommand, CliRemoveCommand
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc

LOGGER = logging.getLogger("discstore")


class CLIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs, remove_disc: RemoveDisc, edit_disc: EditDisc):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc

    def run(self, command: Union[CliAddCommand, CliListCommand, CliRemoveCommand, CliEditCommand]) -> None:
        if isinstance(command, CliAddCommand):
            self.add_disc_flow(command)
        elif isinstance(command, CliListCommand):
            self.list_discs_flow(command)
        elif isinstance(command, CliRemoveCommand):
            self.remove_disc_flow(command)
        elif isinstance(command, CliEditCommand):
            self.edit_disc_flow(command)
        else:
            LOGGER.error(f"Command not implemented yet: command='{command}'")

    def add_disc_flow(self, command: CliAddCommand) -> None:
        tag = command.tag
        uri = command.uri
        option = DiscOption()
        metadata = DiscMetadata(**command.model_dump())

        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        LOGGER.info("✅ CD successfully added")

    def list_discs_flow(self, command: CliListCommand) -> None:
        discs = self.list_discs.execute()
        if command.mode == "table":
            display_library_table(discs)
            return
        if command.mode == "line":
            display_library_line(discs)
            return
        LOGGER.error(f"Displaying mode not implemented yet: mode='{command.mode}'")

    def remove_disc_flow(self, command: CliRemoveCommand) -> None:
        self.remove_disc.execute(command.tag)
        LOGGER.info("🗑️ CD successfully removed")

    def edit_disc_flow(self, command: CliEditCommand) -> None:
        self.edit_disc.execute(
            command.tag, Disc(uri=command.uri, metadata=DiscMetadata(**command.model_dump()), option=DiscOption())
        )
        LOGGER.info("✅ CD successfully edited")
