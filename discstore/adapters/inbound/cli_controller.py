import logging
from typing import Union

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.adapters.inbound.config import (
    CliAddCommand,
    CliEditCommand,
    CliGetCommand,
    CliListCommand,
    CliRemoveCommand,
    CliSearchCommand,
)
from discstore.domain.entities import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from discstore.domain.use_cases.search_discs import SearchDiscs

LOGGER = logging.getLogger("discstore")


class CLIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        search_discs: SearchDiscs,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_disc = get_disc
        self.search_discs = search_discs

    def run(
        self,
        command: Union[
            CliAddCommand, CliListCommand, CliRemoveCommand, CliEditCommand, CliGetCommand, CliSearchCommand
        ],
    ) -> None:
        if isinstance(command, CliAddCommand):
            self.add_disc_flow(command)
        elif isinstance(command, CliListCommand):
            self.list_discs_flow(command)
        elif isinstance(command, CliRemoveCommand):
            self.remove_disc_flow(command)
        elif isinstance(command, CliEditCommand):
            self.edit_disc_flow(command)
        elif isinstance(command, CliGetCommand):
            self.get_disc_flow(command)
        elif isinstance(command, CliSearchCommand):
            self.search_discs_flow(command)
        else:
            LOGGER.error(f"Command not implemented yet: command='{command}'")

    def add_disc_flow(self, command: CliAddCommand) -> None:
        tag = command.tag
        uri = command.uri
        option = DiscOption()
        metadata = DiscMetadata(**command.model_dump())

        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        LOGGER.info("✅ Disc successfully added")

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
        LOGGER.info("🗑️ Disc successfully removed")

    def edit_disc_flow(self, command: CliEditCommand) -> None:
        metadata_fields = {}
        if command.track is not None:
            metadata_fields["track"] = command.track
        if command.artist is not None:
            metadata_fields["artist"] = command.artist
        if command.album is not None:
            metadata_fields["album"] = command.album

        metadata = DiscMetadata(**metadata_fields) if metadata_fields else None

        self.edit_disc.execute(
            tag_id=command.tag,
            uri=command.uri,
            metadata=metadata,
            option=None,
        )
        LOGGER.info("✅ Disc successfully edited")

    def get_disc_flow(self, command: CliGetCommand) -> None:
        try:
            disc = self.get_disc.execute(command.tag)
            print(f"\n📀 Disc: {command.tag}")
            print(f"  URI      : {disc.uri}")
            print(f"  Artist   : {disc.metadata.artist or '/'}")
            print(f"  Album    : {disc.metadata.album or '/'}")
            print(f"  Track    : {disc.metadata.track or '/'}")
            print(f"  Playlist : {disc.metadata.playlist or '/'}")
            print(f"  Shuffle  : {disc.option.shuffle}")
        except ValueError as e:
            LOGGER.error(str(e))

    def search_discs_flow(self, command: CliSearchCommand) -> None:
        results = self.search_discs.execute(command.query)
        if not results:
            LOGGER.info(f"No discs found matching '{command.query}'")
            return
        LOGGER.info(f"Found {len(results)} disc(s) matching '{command.query}':")
        display_library_table(results)
