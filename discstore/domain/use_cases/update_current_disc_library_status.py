from discstore.domain.entities import CurrentDisc
from discstore.domain.repositories import CurrentDiscRepository


class UpdateCurrentDiscLibraryStatus:
    def __init__(self, repository: CurrentDiscRepository):
        self.repository = repository

    def execute(self, tag_id: str, known_in_library: bool) -> None:
        current_disc = self.repository.get()
        if current_disc is None or current_disc.tag_id != tag_id or current_disc.known_in_library == known_in_library:
            return

        self.repository.save(CurrentDisc(tag_id=tag_id, known_in_library=known_in_library))
