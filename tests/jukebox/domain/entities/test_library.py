from discstore.domain.entities import Disc, DiscMetadata, Library


def test_library():
    discs = {"tag:123": Disc(uri="uri:123", metadata=DiscMetadata())}
    library = Library(discs=discs)
    assert library.discs == discs
