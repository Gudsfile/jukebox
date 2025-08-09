import logging
from typing import Optional

from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs

LOGGER = logging.getLogger("discstore")


class InteractiveCLIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs):
        self.add_disc = add_disc
        self.list_discs = list_discs

    def run(self) -> None:
        while True:
            print("\n=== Discstore management ===")
            print("1. Add a CD")
            print("3. List all CDs")
            print("5. Exit")

            choix = input("Votre choix : ")
            self.handle_command(choix)

    def handle_command(self, command: str, args: Optional[dict] = None) -> None:
        args = args or {}
        try:
            if command in ("1", "add"):
                self.add_discs_flow()
            elif command in ("3", "list"):
                self.list_discs_flow()
            elif command in ("5"):
                print("See you soon!")
                exit(0)
            else:
                print("Invalid choice")
        except Exception as err:
            print(f"Error: {err}")
            LOGGER.error("Error during handling command", err)

    def add_discs_flow(self) -> None:
        print("\n-- Ajouter un CD --")
        tag = input("Tag : ").strip()
        uri = input("URI : ").strip()
        option = DiscOption()
        metadata = DiscMetadata()

        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        print("✅ CD ajouté avec succès.")

    def list_discs_flow(self) -> None:
        print("\n-- Lister les CD --")
        mode = input("Mode : ").strip()

        discs = self.list_discs.execute()
        if mode == "table":
            display_library_table(discs)
            return
        if mode == "line":
            display_library_line(discs)
            return
        print(f"Displaying mode not implemented yet: {mode}")
