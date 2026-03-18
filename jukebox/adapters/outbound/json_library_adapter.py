import json
import logging
import os
import tempfile
from contextlib import suppress
from typing import Optional

from pydantic import ValidationError

from jukebox.domain.entities import Disc, DiscMetadata, DiscOption, Library
from jukebox.domain.repositories import LibraryRepository

LOGGER = logging.getLogger("jukebox")


class JsonLibraryAdapter(LibraryRepository):
    """JSON file-based implementation of LibraryRepository."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._cached_library: Optional[Library] = None
        self._cached_file_state: Optional[tuple[int, int]] = None

    def _load_from_disk(self) -> Library:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Library.model_validate(data)
        except FileNotFoundError as err:
            LOGGER.warning(f"File not found, continuing with an empty library: filepath: {self.filepath}, error: {err}")
            return Library()
        except (json.JSONDecodeError, ValidationError) as err:
            LOGGER.warning(
                f"Error deserializing library, continuing with empty library: filepath: {self.filepath}, error: {err}"
            )
            return Library()

    def _write_library(self, library: Library) -> None:
        directory = os.path.dirname(self.filepath) or "."
        temp_fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".library-", suffix=".json")

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as file_obj:
                json.dump(library.model_dump(), file_obj, indent=2, ensure_ascii=False)
                file_obj.flush()
                os.fsync(file_obj.fileno())

            os.replace(temp_path, self.filepath)

            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except Exception:
            with suppress(FileNotFoundError):
                os.unlink(temp_path)
            raise

    def _get_file_state(self) -> Optional[tuple[int, int]]:
        try:
            stat_result = os.stat(self.filepath)
        except FileNotFoundError:
            return None

        return stat_result.st_mtime_ns, stat_result.st_size

    def _update_cache(self, library: Library) -> None:
        self._cached_library = library.model_copy(deep=True)
        self._cached_file_state = self._get_file_state()

    def _get_cached_library(self) -> Library:
        file_state = self._get_file_state()
        if self._cached_library is not None and self._cached_file_state == file_state:
            return self._cached_library

        library = self._load_from_disk()
        self._cached_library = library
        self._cached_file_state = file_state
        return library

    @staticmethod
    def _copy_disc(disc: Disc) -> Disc:
        return disc.model_copy(deep=True)

    def _persist_library(self, library: Library) -> None:
        self._write_library(library)
        self._update_cache(library)

    def list_discs(self) -> dict[str, Disc]:
        return {tag_id: self._copy_disc(disc) for tag_id, disc in self._get_cached_library().discs.items()}

    def get_disc(self, tag_id: str) -> Optional[Disc]:
        disc = self._get_cached_library().discs.get(tag_id)
        if disc is None:
            return None

        return self._copy_disc(disc)

    def add_disc(self, tag_id: str, disc: Disc) -> None:
        library = self._get_cached_library()
        if tag_id in library.discs:
            raise ValueError(f"Already existing tag: tag_id='{tag_id}'")

        updated_library = library.model_copy(deep=True)
        updated_library.discs[tag_id] = self._copy_disc(disc)
        self._persist_library(updated_library)

    def edit_disc(
        self,
        tag_id: str,
        uri: Optional[str] = None,
        metadata: Optional[DiscMetadata] = None,
        option: Optional[DiscOption] = None,
    ) -> None:
        library = self._get_cached_library()
        current_disc = library.discs.get(tag_id)
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

        updated_library = library.model_copy(deep=True)
        updated_library.discs[tag_id] = Disc(uri=new_uri, metadata=new_metadata, option=new_option)
        self._persist_library(updated_library)

    def remove_disc(self, tag_id: str) -> None:
        library = self._get_cached_library()
        if tag_id not in library.discs:
            raise ValueError(f"Tag does not exist: tag_id='{tag_id}'")

        updated_library = library.model_copy(deep=True)
        updated_library.discs.pop(tag_id)
        self._persist_library(updated_library)

    def search_discs(self, query: str) -> dict[str, Disc]:
        query_lower = query.lower()
        results = {}

        for tag_id, disc in self._get_cached_library().discs.items():
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
