from discstore.domain.entities.disc import Disc, DiscMetadata
from discstore.domain.entities.library import Library


def test_library():
    discs = {"tag:123": Disc(uri="uri:123", metadata=DiscMetadata())}
    library = Library(discs=discs)
    assert library.discs == discs
