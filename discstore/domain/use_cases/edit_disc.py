from typing import Optional

from discstore.domain.entities import Disc, DiscMetadata, DiscOption
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
        current_disc = self.repository.get_disc(tag_id)
        if current_disc is None:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        updated_uri = current_disc.uri if uri is None else uri

        updated_metadata = current_disc.metadata.model_copy(deep=True)
        if metadata is not None:
            metadata_data = current_disc.metadata.model_dump()
            metadata_data.update(metadata.model_dump(exclude_unset=True, exclude_none=True))
            updated_metadata = DiscMetadata(**metadata_data)

        updated_option = current_disc.option.model_copy(deep=True)
        if option is not None:
            option_data = current_disc.option.model_dump()
            option_data.update(option.model_dump(exclude_unset=True, exclude_none=True))
            updated_option = DiscOption(**option_data)

        self.repository.update_disc(
            tag_id,
            Disc(uri=updated_uri, metadata=updated_metadata, option=updated_option),
        )
