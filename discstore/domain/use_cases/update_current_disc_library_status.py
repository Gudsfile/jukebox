from discstore.domain.entities import CurrentDisc
from discstore.domain.repositories import CurrentDiscRepository


class UpdateCurrentDiscLibraryStatus:
    def __init__(self, repository: CurrentDiscRepository):
        self.repository = repository

    def execute(self, tag_id: str, known_in_library: bool) -> None:
        self.repository.save_if_matches(
            expected_current_disc=CurrentDisc(tag_id=tag_id, known_in_library=not known_in_library),
            new_current_disc=CurrentDisc(tag_id=tag_id, known_in_library=known_in_library),
        )
