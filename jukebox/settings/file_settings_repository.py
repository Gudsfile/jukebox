import json
import os
import tempfile
from contextlib import suppress
from typing import Optional

from pydantic import ValidationError

from .dict_utils import deep_merge
from .entities import PersistedAppSettings, SparsePersistedAppSettings
from .errors import InvalidSettingsError, MalformedSettingsFileError
from .migration import CURRENT_SETTINGS_SCHEMA_VERSION, migrate_settings_data
from .types import JsonObject


class FileSettingsRepository:
    def __init__(self, filepath: Optional[str] = None):
        if filepath is None:
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
            self.filepath = os.path.expanduser(os.path.join(xdg_config_home, "jukebox/settings.json"))
        else:
            self.filepath = os.path.expanduser(filepath)

    def load_persisted_settings_data(self) -> JsonObject:
        if not os.path.exists(self.filepath):
            return {"schema_version": CURRENT_SETTINGS_SCHEMA_VERSION}

        try:
            with open(self.filepath, "r", encoding="utf-8") as file_obj:
                raw_data = json.load(file_obj)
        except json.JSONDecodeError as err:
            raise MalformedSettingsFileError(f"Malformed settings file at '{self.filepath}': {err}") from err

        migrated_data, migrated = migrate_settings_data(raw_data)

        try:
            SparsePersistedAppSettings.model_validate(migrated_data)
            PersistedAppSettings.model_validate(
                deep_merge(PersistedAppSettings().model_dump(mode="python"), migrated_data)
            )
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings file at '{self.filepath}': {err}") from err

        if migrated:
            self._write_data(migrated_data)

        return migrated_data

    def load_persisted(self) -> PersistedAppSettings:
        raw_data = self.load_persisted_settings_data()

        try:
            return PersistedAppSettings.model_validate(
                deep_merge(PersistedAppSettings().model_dump(mode="python"), raw_data)
            )
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings file at '{self.filepath}': {err}") from err

    def save_persisted_settings_data(self, data: JsonObject) -> None:
        self._write_data(data)

    def _write_data(self, data: JsonObject) -> None:
        directory = os.path.dirname(self.filepath) or "."
        os.makedirs(directory, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".settings-", suffix=".json")

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as file_obj:
                json.dump(data, file_obj, indent=2, ensure_ascii=False)
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
