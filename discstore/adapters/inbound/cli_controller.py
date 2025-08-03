from discstore.adapters.inbound.cli_display import display_library_line, display_library_table
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs


class CLIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs):
        self.add_disc = add_disc
        self.list_discs = list_discs

    def run(self) -> None:
        while True:
            print("\n--- Gestionnaire de Discothèque ---")
            print("1. Ajouter un CD")
            print("3. Lister les CD")
            print("5. Quitter")

            choix = input("Votre choix : ")

            try:
                if choix == "1":
                    self.add_discs_flow()
                elif choix == "3":
                    self.list_discs_flow()
                elif choix == "5":
                    print("À bientôt !")
                    break
                else:
                    print("Choix invalide.")
            except Exception as e:
                print(f"[ERREUR] {e}")

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
