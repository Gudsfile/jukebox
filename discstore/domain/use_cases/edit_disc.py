from typing import Optional

from discstore.domain.entities import DiscMetadata, DiscOption
from discstore.domain.repositories import LibraryRepository


class EditDisc:
    def __init__(self, repository: LibraryRepository):
        self.repository = repository

    def execute(
        self,
        tag_id: str,
        uri: Optional[str] = None,
        metadata: Optional[DiscMetadata] = None,
        option: Optional[DiscOption] = None,
    ) -> None:
        self.repository.edit_disc(tag_id, uri=uri, metadata=metadata, option=option)
