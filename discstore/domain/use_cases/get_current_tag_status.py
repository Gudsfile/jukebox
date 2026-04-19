from discstore.domain.entities import CurrentTagStatus
from discstore.domain.repositories import CurrentTagRepository, LibraryRepository


class GetCurrentTagStatus:
    def __init__(self, current_tag_repository: CurrentTagRepository, library: LibraryRepository):
        self.current_tag_repository = current_tag_repository
        self.library = library

    def execute(self) -> CurrentTagStatus | None:
        tag_id = self.current_tag_repository.get()
        if tag_id is None:
            return None

        return CurrentTagStatus(tag_id=tag_id, known_in_library=self.library.get_disc(tag_id) is not None)
