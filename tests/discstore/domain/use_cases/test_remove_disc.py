from typing import Optional

import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository
from discstore.domain.use_cases.remove_disc import RemoveDisc


class FakeRepo(LibraryRepository):
    def __init__(self):
        self.saved_library: Optional[Library] = None
        self.library = Library(discs={"tag42": Disc(uri="/existing.mp3", metadata=DiscMetadata())})

    def load(self):
        return self.library

    def save(self, library: Library):
        self.saved_library = library


def test_remove_disc_adds_disc():
    repo = FakeRepo()
    use_case = RemoveDisc(repo)

    use_case.execute("tag42")

    assert repo.saved_library is not None
    assert "tag42" not in repo.saved_library.discs
    assert repo.saved_library.discs == {}


def test_remove_disc_fails_if_tag_exists():
    repo = FakeRepo()
    use_case = RemoveDisc(repo)

    with pytest.raises(ValueError) as exc:
        use_case.execute("tag44")

    assert "Tag does not exist: tag_id='tag44'" in str(exc.value)
