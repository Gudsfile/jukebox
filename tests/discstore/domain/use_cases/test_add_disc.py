from typing import Optional

import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository
from discstore.domain.use_cases.add_disc import AddDisc


class FakeRepo(LibraryRepository):
    def __init__(self):
        self.saved_library: Optional[Library] = None
        self.library = Library(discs={"existing-tag": Disc(uri="/existing.mp3", metadata=DiscMetadata())})

    def load(self):
        return self.library

    def save(self, library: Library):
        self.saved_library = library


def test_add_disc_adds_disc():
    repo = FakeRepo()
    use_case = AddDisc(repo)

    new_disc = Disc(uri="/new.mp3", metadata=DiscMetadata())
    use_case.execute("non-existing-tag", new_disc)

    assert repo.saved_library is not None
    assert len(repo.saved_library.discs) == 2
    assert "existing-tag" in repo.saved_library.discs
    assert repo.saved_library.discs["existing-tag"] != new_disc
    assert "non-existing-tag" in repo.saved_library.discs
    assert repo.saved_library.discs["non-existing-tag"] == new_disc


def test_add_disc_fails_if_tag_exists():
    repo = FakeRepo()
    use_case = AddDisc(repo)

    new_disc = Disc(uri="/new.mp3", metadata=DiscMetadata())
    with pytest.raises(ValueError) as exc:
        use_case.execute("existing-tag", new_disc)

    assert "Already existing tag: tag_id='existing-tag'" in str(exc.value)
    assert repo.saved_library is None
