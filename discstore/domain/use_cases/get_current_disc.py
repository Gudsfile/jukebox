from typing import Optional

from discstore.domain.entities import CurrentDisc
from jukebox.domain.repositories import CurrentTagRepository, LibraryRepository


class GetCurrentDisc:
    def __init__(self, current_tag_repository: CurrentTagRepository, library: LibraryRepository):
        self.current_tag_repository = current_tag_repository
        self.library = library

    def execute(self) -> Optional[CurrentDisc]:
        tag_id = self.current_tag_repository.get()
        if tag_id is None:
            return None

        return CurrentDisc(tag_id=tag_id, known_in_library=self.library.get_disc(tag_id) is not None)
