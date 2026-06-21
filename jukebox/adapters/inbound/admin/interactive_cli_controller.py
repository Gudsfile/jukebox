import typer

from jukebox.adapters.inbound.admin.cli_display import display_library_line, display_library_table
from jukebox.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
from jukebox.domain.use_cases import AddDisc, EditDisc, GetCurrentTagStatus, ListDiscs, RemoveDisc


class InteractiveCLIController:
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_current_tag_status: GetCurrentTagStatus,
    ):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.get_current_tag_status = get_current_tag_status

    def run(self) -> None:
        import questionary

        while True:
            try:
                command = questionary.select(
                    "What do you want to do?",
                    choices=["add", "remove", "list", "edit", "current"],
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
                    case "current":
                        self.current_tag_flow()
            except KeyboardInterrupt:
                return
            except Exception as err:
                typer.echo(f"Error: {err}", err=True)

    def add_disc_flow(self) -> None:
        import questionary

        print("\n-- Add a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="add")
        uri = questionary.text("URI:").unsafe_ask()
        disc = Disc(uri=uri.strip(), metadata=DiscMetadata(), option=DiscOption())
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
        tag = questionary.text("Tag ID:").unsafe_ask()
        self.remove_disc.execute(tag.strip())
        print("🗑️ Disc successfully removed")

    def edit_disc_flow(self) -> None:
        import questionary

        print("\n-- Edit a disc --")
        current_tag_status = self.get_current_tag_status.execute()
        tag = self._prompt_for_tag(current_tag_status, action="edit")
        uri = questionary.text("URI:").unsafe_ask()
        self.edit_disc.execute(tag, uri.strip(), DiscMetadata(), DiscOption())
        print("✅ Disc successfully edited")

    def current_tag_flow(self) -> None:
        print("\n-- Current tag --")
        current_tag_status = self.get_current_tag_status.execute()
        if current_tag_status is None:
            print("No current tag is available")
            return

        print(f"Tag ID           : {current_tag_status.tag_id}")
        print(f"Known in library : {'yes' if current_tag_status.known_in_library else 'no'}")

    def _prompt_for_tag(self, current_tag_status: CurrentTagStatus | None, action: str) -> str:
        import questionary

        default_tag = ""
        if current_tag_status is not None and (
            (action == "add" and not current_tag_status.known_in_library)
            or (action == "edit" and current_tag_status.known_in_library)
        ):
            default_tag = current_tag_status.tag_id

        entered_tag = questionary.text(f"Tag ID ({action}):", default=default_tag).unsafe_ask()
        tag = (entered_tag or "").strip() or default_tag
        if not tag:
            raise ValueError("A tag ID is required.")
        return tag
