import pytest

from discstore.domain.entities import Disc, DiscMetadata, Library
from discstore.domain.use_cases.edit_disc import EditDisc
from tests.discstore.domain.use_cases.mock_repo import MockRepo


@pytest.fixture
def repo():
    return MockRepo(Library(discs={"existing-tag": Disc(uri="/existing.mp3", metadata=DiscMetadata())}))


def test_edit_disc_edits_disc(repo):
    use_case = EditDisc(repo)

    use_case.execute("existing-tag", uri="/new.mp3")

    assert repo.saved_library is not None
    assert len(repo.saved_library.discs) == 1
    assert "existing-tag" in repo.saved_library.discs
    assert repo.saved_library.discs["existing-tag"].uri == "/new.mp3"


def test_edit_disc_fails_if_tag_does_not_exists(repo):
    use_case = EditDisc(repo)

    with pytest.raises(ValueError) as exc:
        use_case.execute("non-existing-tag", uri="/new.mp3")

    assert "Tag does not exist: tag_id='non-existing-tag'" in str(exc.value)
    assert repo.saved_library is None
