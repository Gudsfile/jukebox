import logging
import os
import tempfile
from typing import Optional

from shared_storage.current_tag_paths import get_current_tag_path
from shared_storage.current_tag_repository import CurrentTagRepository

LOGGER = logging.getLogger("jukebox")


class TextCurrentTagAdapter(CurrentTagRepository):
    """Plain-text sidecar implementation of CurrentTagRepository.

    Writes are atomic via temp-file replace; the current-tag state has a
    single expected writer, so no cross-process lock file is maintained.
    """

    def __init__(self, library_path: str):
        self.filepath = get_current_tag_path(library_path)

    def get(self) -> Optional[str]:
        return self._read_current_tag()

    def set(self, tag_id: str) -> None:
        directory = os.path.dirname(self.filepath)
        os.makedirs(directory, exist_ok=True)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                delete=False,
                prefix="current-tag-",
                suffix=".tmp",
            ) as temp_file:
                temp_path = temp_file.name
                self._write_text(temp_file, tag_id)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.filepath)
            self._fsync_directory()
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def clear(self) -> None:
        self._clear_unlocked()

    def _read_current_tag(self) -> Optional[str]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as current_tag_file:
                tag_id = current_tag_file.read().strip()
        except FileNotFoundError:
            return None
        except OSError as err:
            LOGGER.warning(f"Error reading current tag state: filepath: {self.filepath}, error: {err}")
            return None

        if not tag_id:
            return None

        return tag_id

    def _clear_unlocked(self) -> None:
        try:
            os.unlink(self.filepath)
            self._fsync_directory()
        except FileNotFoundError:
            return

    def _write_text(self, temp_file, tag_id: str) -> None:
        temp_file.write(f"{tag_id}\n")

    def _fsync_directory(self) -> None:
        directory_fd = os.open(os.path.dirname(self.filepath), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
