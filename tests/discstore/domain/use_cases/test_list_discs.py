from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.use_cases.list_discs import ListDiscs
from tests.discstore.domain.use_cases.mock_repo import MockRepo


def test_list_discs_returns_all_discs():
    discs = {
        "tag1": Disc(uri="/song1.mp3", metadata=DiscMetadata()),
        "tag2": Disc(uri="/song2.mp3", metadata=DiscMetadata()),
    }
    repo = MockRepo(Library(discs=discs))
    use_case = ListDiscs(repo)

    result = use_case.execute()

    assert result == discs
