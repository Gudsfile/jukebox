import json
import logging
import os
import tempfile
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock
from typing import Iterator, Optional

from pydantic import ValidationError

from jukebox.domain.entities import CurrentDisc
from jukebox.domain.repositories import CurrentDiscRepository
from jukebox.shared.config_utils import get_current_disc_lock_path, get_current_disc_path

LOGGER = logging.getLogger("jukebox")


class JsonCurrentDiscAdapter(CurrentDiscRepository):
    """JSON sidecar implementation of CurrentDiscRepository."""

    def __init__(self, library_path: str):
        self.filepath = get_current_disc_path(library_path)
        self.lock_filepath = get_current_disc_lock_path(library_path)

    def get(self) -> Optional[CurrentDisc]:
        with self._exclusive_lock():
            return self._read_current_disc()

    def save(self, current_disc: CurrentDisc) -> None:
        with self._exclusive_lock():
            self._save_unlocked(current_disc)

    def save_if_matches(self, expected_current_disc: CurrentDisc, new_current_disc: CurrentDisc) -> bool:
        with self._exclusive_lock():
            current_disc = self._read_current_disc()
            if current_disc != expected_current_disc:
                return False

            self._save_unlocked(new_current_disc)
            return True

    def clear(self) -> None:
        with self._exclusive_lock():
            self._clear_unlocked()

    def clear_if_matches(self, tag_id: str) -> bool:
        with self._exclusive_lock():
            current_disc = self._read_current_disc()
            if current_disc is None or current_disc.tag_id != tag_id:
                return False

            self._clear_unlocked()
            return True

    def _save_unlocked(self, current_disc: CurrentDisc) -> None:
        directory = os.path.dirname(self.filepath)
        os.makedirs(directory, exist_ok=True)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                delete=False,
                prefix="current-disc-",
                suffix=".tmp",
            ) as temp_file:
                temp_path = temp_file.name
                self._write_json(temp_file, current_disc)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.filepath)
            self._fsync_directory()
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _read_current_disc(self) -> Optional[CurrentDisc]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as current_disc_file:
                return CurrentDisc.model_validate(json.load(current_disc_file))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, ValidationError) as err:
            LOGGER.warning(f"Error deserializing current disc state: filepath: {self.filepath}, error: {err}")
            return None

    def _clear_unlocked(self) -> None:
        try:
            os.unlink(self.filepath)
            self._fsync_directory()
        except FileNotFoundError:
            return

    def _write_json(self, temp_file, current_disc: CurrentDisc) -> None:
        json.dump(current_disc.model_dump(), temp_file, indent=2, ensure_ascii=False)

    def _fsync_directory(self) -> None:
        directory_fd = os.open(os.path.dirname(self.filepath), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        directory = os.path.dirname(self.lock_filepath)
        os.makedirs(directory, exist_ok=True)

        with open(self.lock_filepath, "a+", encoding="utf-8") as lock_file:
            flock(lock_file.fileno(), LOCK_EX)
            try:
                yield
            finally:
                flock(lock_file.fileno(), LOCK_UN)
