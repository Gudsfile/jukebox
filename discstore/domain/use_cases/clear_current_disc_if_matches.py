from discstore.domain.repositories import CurrentDiscRepository


class ClearCurrentDiscIfMatches:
    def __init__(self, repository: CurrentDiscRepository):
        self.repository = repository

    def execute(self, tag_id: str) -> bool:
        return self.repository.clear_if_matches(tag_id)
