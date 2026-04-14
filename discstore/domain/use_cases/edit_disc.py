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
    ) -> Disc:
        current_disc = self.repository.get_disc(tag_id)
        if current_disc is None:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        new_uri = uri if uri is not None else current_disc.uri

        new_metadata = current_disc.metadata
        if metadata is not None:
            current_data = current_disc.metadata.model_dump()
            new_data = metadata.model_dump(exclude_unset=True, exclude_none=True)
            current_data.update(new_data)
            new_metadata = DiscMetadata(**current_data)

        new_option = current_disc.option
        if option is not None:
            current_opt_data = current_disc.option.model_dump()
            new_opt_data = option.model_dump(exclude_unset=True, exclude_none=True)
            current_opt_data.update(new_opt_data)
            new_option = DiscOption(**current_opt_data)

        updated_disc = Disc(uri=new_uri, metadata=new_metadata, option=new_option)
        self.repository.update_disc(tag_id, updated_disc)
        return updated_disc
