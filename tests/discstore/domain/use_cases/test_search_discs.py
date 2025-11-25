from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library
from discstore.domain.use_cases.search_discs import SearchDiscs

from .mock_repo import MockRepo


def test_search_by_artist():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(artist="Pink Floyd")),
                "tag:2": Disc(uri="uri2", metadata=DiscMetadata(artist="The Beatles")),
                "tag:3": Disc(uri="uri3", metadata=DiscMetadata(artist="Pink Panther")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("Pink")

    assert len(results) == 2
    assert "tag:1" in results
    assert "tag:3" in results


def test_search_by_album():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(album="Dark Side of the Moon")),
                "tag:2": Disc(uri="uri2", metadata=DiscMetadata(album="Abbey Road")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("Dark")

    assert len(results) == 1
    assert "tag:1" in results


def test_search_by_track():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(track="Money")),
                "tag:2": Disc(uri="uri2", metadata=DiscMetadata(track="Time")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("money")

    assert len(results) == 1
    assert "tag:1" in results


def test_search_by_tag_id():
    repo = MockRepo(
        Library(
            discs={
                "tag:pink:floyd": Disc(uri="uri1", metadata=DiscMetadata(artist="Pink Floyd")),
                "tag:beatles": Disc(uri="uri2", metadata=DiscMetadata(artist="The Beatles")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("pink")

    assert len(results) == 1
    assert "tag:pink:floyd" in results


def test_search_case_insensitive():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(artist="PINK FLOYD")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("pink floyd")

    assert len(results) == 1


def test_search_no_results():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(artist="Artist")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("nonexistent")

    assert len(results) == 0


def test_search_multiple_fields():
    repo = MockRepo(
        Library(
            discs={
                "tag:1": Disc(uri="uri1", metadata=DiscMetadata(artist="Test Artist", album="Album")),
                "tag:2": Disc(uri="uri2", metadata=DiscMetadata(artist="Artist", album="Test Album")),
                "tag:3": Disc(uri="uri3", metadata=DiscMetadata(artist="Other", track="Test Track")),
            }
        )
    )
    use_case = SearchDiscs(repo)

    results = use_case.execute("Test")

    assert len(results) == 3
