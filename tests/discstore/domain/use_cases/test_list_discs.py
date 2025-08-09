from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository
from discstore.domain.use_cases.list_discs import ListDiscs


class FakeRepo(LibraryRepository):
    def __init__(self, discs):
        self.library = Library(discs=discs)

    def load(self):
        return self.library

    def save(self, library: Library):
        pass


def test_list_discs_returns_all_discs():
    discs = {
        "tag1": Disc(uri="/song1.mp3", metadata=DiscMetadata()),
        "tag2": Disc(uri="/song2.mp3", metadata=DiscMetadata()),
    }
    repo = FakeRepo(discs)
    use_case = ListDiscs(repo)

    result = use_case.execute()

    assert result == discs
