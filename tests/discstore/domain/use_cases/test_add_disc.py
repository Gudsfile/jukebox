import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.use_cases.add_disc import AddDisc
from tests.discstore.domain.use_cases.mock_repo import MockRepo


@pytest.fixture
def repo():
    return MockRepo(Library(discs={"existing-tag": Disc(uri="/existing.mp3", metadata=DiscMetadata())}))


def test_add_disc_adds_disc(repo):
    use_case = AddDisc(repo)

    new_disc = Disc(uri="/new.mp3", metadata=DiscMetadata())
    use_case.execute("non-existing-tag", new_disc)

    assert repo.saved_library is not None
    assert len(repo.saved_library.discs) == 2
    assert "existing-tag" in repo.saved_library.discs
    assert repo.saved_library.discs["existing-tag"] != new_disc
    assert "non-existing-tag" in repo.saved_library.discs
    assert repo.saved_library.discs["non-existing-tag"] == new_disc


def test_add_disc_fails_if_tag_exists(repo):
    use_case = AddDisc(repo)

    new_disc = Disc(uri="/new.mp3", metadata=DiscMetadata())
    with pytest.raises(ValueError) as exc:
        use_case.execute("existing-tag", new_disc)

    assert "Already existing tag: tag_id='existing-tag'" in str(exc.value)
    assert repo.saved_library is None
