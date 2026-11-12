import pytest

from jukebox.domain.entities import Disc, DiscMetadata, Library, LibraryImportSummary
from jukebox.domain.use_cases.library.import_library import ImportLibrary, PreviewLibraryImport
from tests.jukebox.domain.use_cases.library.mock_repo import MockRepo


@pytest.fixture
def repo():
    return MockRepo(
        Library(
            discs={
                "kept-tag": Disc(uri="/kept.mp3", metadata=DiscMetadata()),
                "changed-tag": Disc(uri="/before.mp3", metadata=DiscMetadata()),
                "removed-tag": Disc(uri="/removed.mp3", metadata=DiscMetadata()),
            }
        )
    )


@pytest.fixture
def imported():
    return Library(
        discs={
            "kept-tag": Disc(uri="/kept.mp3", metadata=DiscMetadata()),
            "changed-tag": Disc(uri="/after.mp3", metadata=DiscMetadata()),
            "added-tag": Disc(uri="/added.mp3", metadata=DiscMetadata()),
        }
    )


def test_preview_library_import_summarizes_differences(repo, imported):
    summary = PreviewLibraryImport(repo).execute(imported)

    assert summary == LibraryImportSummary(
        disc_count=3,
        added=["added-tag"],
        changed=["changed-tag"],
        removed=["removed-tag"],
    )


def test_preview_library_import_does_not_write(repo, imported):
    PreviewLibraryImport(repo).execute(imported)

    assert repo.replace_calls == []
    assert set(repo.library.discs) == {"kept-tag", "changed-tag", "removed-tag"}


def test_preview_library_import_into_empty_library_lists_every_tag_as_added(imported):
    summary = PreviewLibraryImport(MockRepo(Library())).execute(imported)

    assert summary.added == ["added-tag", "changed-tag", "kept-tag"]
    assert summary.changed == []
    assert summary.removed == []


def test_import_library_replaces_whole_library(repo, imported):
    ImportLibrary(repo).execute(imported)

    assert repo.replace_calls == [imported]
    assert repo.library == imported
