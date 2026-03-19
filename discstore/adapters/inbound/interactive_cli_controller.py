import logging
from typing import Optional

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.domain.entities import CurrentDisc, Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_disc import GetCurrentDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc

LOGGER = logging.getLogger("discstore")


class InteractiveCLIController:
    available_commands = "\n* " + "\n* ".join(["add", "remove", "list", "edit", "current", "exit", "help"])
    help_message = f"\nAvailable commands: {available_commands}"

    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_current_disc: GetCurrentDisc,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_current_disc = get_current_disc

    def run(self) -> None:
        print(self.help_message)
        while True:
            command = input("discstore> ")
            self.handle_command(command)

    def handle_command(self, command: str) -> None:
        try:
            if command == "add":
                self.add_disc_flow()
            elif command == "remove":
                self.remove_disc_flow()
            elif command == "list":
                self.list_discs_flow()
            elif command == "edit":
                self.edit_disc_flow()
            elif command == "current":
                self.current_disc_flow()
            elif command == "exit":
                print("See you soon!")
                exit(0)
            elif command == "help":
                print(self.help_message)
            else:
                print(f"Invalid command `{command}`")
                print(self.help_message)
        except Exception as err:
            print(f"Error: {err}")
            LOGGER.error("Error during handling command: %s", err)

    def add_disc_flow(self) -> None:
        print("\n-- Add a disc --")
        current_disc = self.get_current_disc.execute()
        tag = self._prompt_for_tag(current_disc, action="add")
        uri = input("discstore> add uri> ").strip()
        option = DiscOption()
        metadata = DiscMetadata()

        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        print("✅ Disc successfully added")

    def list_discs_flow(self) -> None:
        print("\n-- List all discs --")
        mode = input("discstore> list mode(table/line)> ").strip()

        discs = self.list_discs.execute()
        if mode == "table" or mode == "":
            display_library_table(discs)
            return
        if mode == "line":
            display_library_line(discs)
            return
        print(f"Displaying mode not implemented yet: `{mode}`")

    def remove_disc_flow(self) -> None:
        print("\n-- Remove a disc --")
        tag = input("discstore> remove tag> ").strip()
        self.remove_disc.execute(tag)
        print("🗑️ Disc successfully removed")

    def edit_disc_flow(self) -> None:
        print("\n-- Edit a disc --")
        current_disc = self.get_current_disc.execute()
        tag = self._prompt_for_tag(current_disc, action="edit")
        uri = input("discstore> edit uri> ").strip()
        option = DiscOption()
        metadata = DiscMetadata()

        self.edit_disc.execute(tag, uri, metadata, option)
        print("✅ Disc successfully edited")

    def current_disc_flow(self) -> None:
        print("\n-- Current disc --")
        current_disc = self.get_current_disc.execute()
        if current_disc is None:
            print("No current disc is available")
            return

        print(f"Tag ID           : {current_disc.tag_id}")
        print(f"Known in library : {'yes' if current_disc.known_in_library else 'no'}")

    def _prompt_for_tag(self, current_disc: Optional[CurrentDisc], action: str) -> str:
        default_tag = current_disc.tag_id if current_disc is not None else ""
        prompt = f"discstore> {action} tag"
        if default_tag:
            prompt += f" [{default_tag}]"
        prompt += "> "

        entered_tag = input(prompt).strip()
        tag = entered_tag or default_tag
        if not tag:
            raise ValueError("A tag ID is required.")

        return tag
