import pytest

from discstore.domain.entities import Disc, DiscMetadata, Library
from discstore.domain.use_cases.remove_disc import RemoveDisc
from tests.discstore.domain.use_cases.mock_repo import MockRepo


@pytest.fixture
def repo():
    return MockRepo(Library(discs={"existing-tag": Disc(uri="/existing.mp3", metadata=DiscMetadata())}))


def test_remove_disc_removes_disc(repo):
    use_case = RemoveDisc(repo)

    use_case.execute("existing-tag")

    assert repo.saved_library is not None
    assert repo.saved_library.discs == {}


def test_remove_disc_fails_if_tag_does_not_exists(repo):
    use_case = RemoveDisc(repo)

    with pytest.raises(ValueError) as exc:
        use_case.execute("non-existing-tag")

    assert "Tag does not exist: tag_id='non-existing-tag'" in str(exc.value)
