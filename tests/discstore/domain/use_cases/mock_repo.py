from typing import Optional

from discstore.domain.entities import Disc, DiscMetadata, DiscOption, Library
from discstore.domain.repositories import LibraryRepository


class MockRepo(LibraryRepository):
    def __init__(self, library: Library):
        self.library = library.model_copy(deep=True)
        self.add_calls: list[tuple[str, Disc]] = []
        self.edit_calls: list[tuple[str, Optional[str], Optional[DiscMetadata], Optional[DiscOption]]] = []
        self.remove_calls: list[str] = []
        self.get_calls: list[str] = []
        self.search_calls: list[str] = []
        self.list_calls = 0

    @staticmethod
    def _copy_disc(disc: Disc) -> Disc:
        return disc.model_copy(deep=True)

    def list_discs(self):
        self.list_calls += 1
        return {tag_id: self._copy_disc(disc) for tag_id, disc in self.library.discs.items()}

    def get_disc(self, tag_id: str):
        self.get_calls.append(tag_id)
        disc = self.library.discs.get(tag_id)
        if disc is None:
            return None

        return self._copy_disc(disc)

    def add_disc(self, tag_id: str, disc: Disc):
        self.add_calls.append((tag_id, self._copy_disc(disc)))
        if tag_id in self.library.discs:
            raise ValueError(f"Already existing tag: tag_id='{tag_id}'")

        self.library.discs[tag_id] = self._copy_disc(disc)

    def edit_disc(
        self,
        tag_id: str,
        uri: Optional[str] = None,
        metadata: Optional[DiscMetadata] = None,
        option: Optional[DiscOption] = None,
    ):
        metadata_copy = None if metadata is None else metadata.model_copy(deep=True)
        option_copy = None if option is None else option.model_copy(deep=True)
        self.edit_calls.append((tag_id, uri, metadata_copy, option_copy))

        current_disc = self.library.discs.get(tag_id)
        if current_disc is None:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        new_uri = current_disc.uri if uri is None else uri

        new_metadata = current_disc.metadata.model_copy(deep=True)
        if metadata is not None:
            current_data = current_disc.metadata.model_dump()
            new_data = metadata.model_dump(exclude_unset=True, exclude_none=True)
            current_data.update(new_data)
            new_metadata = DiscMetadata(**current_data)

        new_option = current_disc.option.model_copy(deep=True)
        if option is not None:
            current_opt_data = current_disc.option.model_dump()
            new_opt_data = option.model_dump(exclude_unset=True, exclude_none=True)
            current_opt_data.update(new_opt_data)
            new_option = DiscOption(**current_opt_data)

        self.library.discs[tag_id] = Disc(uri=new_uri, metadata=new_metadata, option=new_option)

    def remove_disc(self, tag_id: str):
        self.remove_calls.append(tag_id)
        if tag_id not in self.library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        self.library.discs.pop(tag_id)

    def search_discs(self, query: str):
        self.search_calls.append(query)
        query_lower = query.lower()
        results = {}

        for tag_id, disc in self.library.discs.items():
            if query_lower in tag_id.lower():
                results[tag_id] = self._copy_disc(disc)
                continue

            metadata = disc.metadata
            if (
                (metadata.artist and query_lower in metadata.artist.lower())
                or (metadata.album and query_lower in metadata.album.lower())
                or (metadata.track and query_lower in metadata.track.lower())
                or (metadata.playlist and query_lower in metadata.playlist.lower())
            ):
                results[tag_id] = self._copy_disc(disc)

        return results
