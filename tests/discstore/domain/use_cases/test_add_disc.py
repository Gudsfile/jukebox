from typing import Optional

import pytest

from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.repositories.library_repository import LibraryRepository
from discstore.domain.use_cases.add_disc import AddDisc


class FakeRepo(LibraryRepository):
    def __init__(self):
        self.saved_library: Optional[Library] = None
        self.library = Library(discs={})

    def load(self):
        return self.library

    def save(self, library: Library):
        self.saved_library = library


def test_add_disc_adds_disc():
    repo = FakeRepo()
    use_case = AddDisc(repo)

    disc = Disc(uri="/music.mp3", metadata=DiscMetadata())
    use_case.execute("tag42", disc)

    assert repo.saved_library is not None
    assert "tag42" in repo.saved_library.discs
    assert repo.saved_library.discs["tag42"] == disc


def test_add_disc_fails_if_tag_exists():
    repo = FakeRepo()
    existing_disc = Disc(uri="/existing.mp3", metadata=DiscMetadata())
    repo.library.discs["tag42"] = existing_disc

    use_case = AddDisc(repo)
    new_disc = Disc(uri="/new.mp3", metadata=DiscMetadata())

    with pytest.raises(ValueError) as exc:
        use_case.execute("tag42", new_disc)

    assert "Already existing tag: tag_id='tag42'" in str(exc.value)
