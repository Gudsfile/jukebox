from typing import Literal

import typer

from jukebox.adapters.inbound.admin.cli_display import (
    build_remove_confirmation,
    display_disc,
    display_library_line,
    display_library_table,
)
from jukebox.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
from jukebox.domain.use_cases import AddDisc, EditDisc, GetCurrentTagStatus, GetDisc, ListDiscs, RemoveDisc, SearchDiscs


class InteractiveCLIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        get_current_tag_status: GetCurrentTagStatus,
        search_discs: SearchDiscs,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_disc = get_disc
        self.get_current_tag_status = get_current_tag_status
        self.search_discs = search_discs

    def run(self) -> None:
        import questionary

        while True:
            try:
                command = questionary.select(
                    "What do you want to do?",
                    choices=["add", "remove", "list", "edit", "get", "search", "current"],
                ).unsafe_ask()
            except KeyboardInterrupt:
                return

            try:
                match command:
                    case "add":
                        self.add_disc_flow()
                    case "remove":
                        self.remove_disc_flow()
                    case "list":
                        self.list_discs_flow()
                    case "edit":
                        self.edit_disc_flow()
                    case "get":
                        self.get_disc_flow()
                    case "search":
                        self.search_discs_flow()
                    case "current":
                        self.current_tag_flow()
            except KeyboardInterrupt:
                return
            except Exception as err:
                typer.echo(f"Error: {err}", err=True)

    def add_disc_flow(self) -> None:
        print("\n-- Add a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="add")
        uri = self._prompt_for_uri()
        metadata = self._prompt_for_metadata()
        option = self._prompt_for_option()
        disc = Disc(uri=uri, metadata=metadata, option=option)
        self.add_disc.execute(tag, disc)
        print("✅ Disc successfully added")

    def list_discs_flow(self) -> None:
        import questionary

        print("\n-- List all discs --")
        mode = questionary.select(
            "Display mode:",
            choices=["table", "line"],
        ).unsafe_ask()

        discs = self.list_discs.execute()
        if mode == "table":
            display_library_table(discs)
        else:
            display_library_line(discs)

    def remove_disc_flow(self) -> None:
        import questionary

        print("\n-- Remove a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="remove")
        disc = self.get_disc.execute(tag)
        if not questionary.confirm(build_remove_confirmation(tag, disc), default=False).unsafe_ask():
            print("Disc not removed")
            return
        self.remove_disc.execute(tag)
        print("🗑️ Disc successfully removed")

    def edit_disc_flow(self) -> None:
        print("\n-- Edit a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="edit")
        current_disc = self.get_disc.execute(tag)
        uri = self._prompt_for_uri(current_disc.uri)
        metadata = self._prompt_for_metadata(current_disc.metadata)
        option = self._prompt_for_option(current_disc.option)
        self.edit_disc.execute(tag, uri, metadata, option)
        print("✅ Disc successfully edited")

    def get_disc_flow(self) -> None:
        print("\n-- Get a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="get")
        disc = self.get_disc.execute(tag)
        display_disc(tag, disc)

    def search_discs_flow(self) -> None:
        import questionary

        print("\n-- Search discs --")
        query = questionary.text("Query:").unsafe_ask().strip()
        if not query:
            raise ValueError("A query is required.")
        results = self.search_discs.execute(query)
        if not results:
            print(f"No discs found matching '{query}'")
            return
        print(f"Found {len(results)} disc(s) matching '{query}':")
        display_library_table(results)

    def current_tag_flow(self) -> None:
        print("\n-- Current tag --")
        current_tag_status = self.get_current_tag_status.execute()
        if current_tag_status is None:
            print("No current tag is available")
            return

        print(f"Tag ID           : {current_tag_status.tag_id}")
        print(f"Known in library : {'yes' if current_tag_status.known_in_library else 'no'}")
        if not current_tag_status.known_in_library:
            return

        metadata = self.get_disc.execute(current_tag_status.tag_id).metadata
        print(f"Type             : {metadata.display_type}")
        print(f"Title            : {metadata.display_title}")

    def _prompt_for_tag(
        self, current_tag_status: CurrentTagStatus | None, action: Literal["add", "edit", "get", "remove"]
    ) -> str:
        import questionary

        default_tag = ""
        if current_tag_status is not None and (
            (action == "add" and not current_tag_status.known_in_library)
            or (action in ("edit", "get", "remove") and current_tag_status.known_in_library)
        ):
            default_tag = current_tag_status.tag_id

        entered_tag = questionary.text(f"Tag ID ({action}):", default=default_tag).unsafe_ask()
        tag = (entered_tag or "").strip() or default_tag
        if not tag:
            raise ValueError("A tag ID is required.")
        return tag

    def _prompt_for_uri(self, current: str | None = None) -> str:
        import questionary

        entered_uri = questionary.text("URI:", default=current or "").unsafe_ask()
        uri = (entered_uri or "").strip() or current
        if not uri:
            raise ValueError("A URI is required.")
        return uri

    def _prompt_for_metadata(self, current: DiscMetadata | None = None) -> DiscMetadata:
        """Ask for each metadata field, prefilled with the current value; an empty answer means no value."""
        import questionary

        hint = " (optional)" if current is None else " (empty to clear)"
        current = current or DiscMetadata()
        values = {}
        for field in ("artist", "album", "track", "playlist"):
            entered = questionary.text(
                f"{field.capitalize()}{hint}:", default=getattr(current, field) or ""
            ).unsafe_ask()
            values[field] = (entered or "").strip() or None
        return DiscMetadata(**values)

    def _prompt_for_option(self, current: DiscOption | None = None) -> DiscOption:
        import questionary

        current = current or DiscOption()
        shuffle = questionary.confirm("Shuffle?", default=current.shuffle).unsafe_ask()
        return DiscOption(shuffle=shuffle)
