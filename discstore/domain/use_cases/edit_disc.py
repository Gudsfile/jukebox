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
        library = self.repository.load()

        if tag_id not in library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        current_disc = library.discs[tag_id]

        new_uri = uri if uri is not None else current_disc.uri

        new_metadata = current_disc.metadata
        if metadata:
            current_data = current_disc.metadata.model_dump()
            new_data = metadata.model_dump(exclude_unset=True, exclude_none=True)
            current_data.update(new_data)
            new_metadata = DiscMetadata(**current_data)

        new_option = current_disc.option
        if option:
            current_opt_data = current_disc.option.model_dump()
            new_opt_data = option.model_dump(exclude_unset=True, exclude_none=True)
            current_opt_data.update(new_opt_data)
            new_option = DiscOption(**current_opt_data)

        updated_disc = Disc(uri=new_uri, metadata=new_metadata, option=new_option)
        library.discs[tag_id] = updated_disc
        self.repository.save(library)
