from typing import Dict

from discstore.domain.entities import Disc
from discstore.domain.repositories import LibraryRepository


class SearchDiscs:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(self, query: str) -> Dict[str, Disc]:
        library = self.repository.load()
        query_lower = query.lower()

        results = {}
        for tag_id, disc in library.discs.items():
            if query_lower in tag_id.lower():
                results[tag_id] = disc
                continue

            metadata = disc.metadata
            if (
                (metadata.artist and query_lower in metadata.artist.lower())
                or (metadata.album and query_lower in metadata.album.lower())
                or (metadata.track and query_lower in metadata.track.lower())
                or (metadata.playlist and query_lower in metadata.playlist.lower())
            ):
                results[tag_id] = disc

        return results
