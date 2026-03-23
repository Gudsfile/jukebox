import json
import os
import tempfile
from contextlib import suppress
from typing import Union

from pydantic import ValidationError

from .dict_utils import deep_merge
from .entities import AppSettings, SparseAppSettings
from .errors import InvalidSettingsError, MalformedSettingsFileError
from .migration import CURRENT_SETTINGS_SCHEMA_VERSION, migrate_settings_data
from .types import JsonObject, JsonValue

DEFAULT_SETTINGS_PATH = os.path.expanduser("~/.jukebox/settings.json")
_MISSING = object()


class FileSettingsRepository:
    def __init__(self, filepath: str = DEFAULT_SETTINGS_PATH):
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
            SparseAppSettings.model_validate(migrated_data)
            AppSettings.model_validate(deep_merge(AppSettings().model_dump(mode="python"), migrated_data))
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings file at '{self.filepath}': {err}") from err

        if migrated:
            self._write_data(migrated_data)

        return migrated_data

    def load(self) -> AppSettings:
        raw_data = self.load_persisted_settings_data()

        try:
            return AppSettings.model_validate(deep_merge(AppSettings().model_dump(mode="python"), raw_data))
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings file at '{self.filepath}': {err}") from err

    def save(self, settings: AppSettings) -> None:
        default_data = AppSettings().model_dump(mode="python")
        current_data = settings.model_dump(mode="python")
        sparse_data = _build_sparse_diff(current_data, default_data)
        sparse_payload = sparse_data if isinstance(sparse_data, dict) else {}
        sparse_payload["schema_version"] = settings.schema_version
        self._write_data(sparse_payload)

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


def _build_sparse_diff(current: JsonValue, default: object) -> Union[JsonValue, object]:
    if isinstance(current, dict) and isinstance(default, dict):
        diff = {}
        for key, current_value in current.items():
            if key == "schema_version":
                continue

            default_value = default.get(key, _MISSING)
            child_diff = _build_sparse_diff(current_value, default_value)
            if child_diff is not _MISSING:
                diff[key] = child_diff

        if diff:
            return diff

        return _MISSING

    if current != default:
        return current

    return _MISSING
