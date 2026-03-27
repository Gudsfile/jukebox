import json

import pytest

from jukebox.settings.errors import InvalidSettingsError, MalformedSettingsFileError
from jukebox.settings.file_settings_repository import FileSettingsRepository


def test_repository_returns_schema_version_only_when_file_missing(tmp_path):
    repository = FileSettingsRepository(str(tmp_path / "settings.json"))

    assert repository.load_persisted_settings_data() == {"schema_version": 1}


def test_repository_rejects_malformed_json(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{bad json", encoding="utf-8")
    repository = FileSettingsRepository(str(settings_path))

    with pytest.raises(MalformedSettingsFileError):
        repository.load_persisted_settings_data()


def test_repository_rejects_unknown_keys(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"schema_version": 1, "paths": {"unknown": "value"}}), encoding="utf-8")
    repository = FileSettingsRepository(str(settings_path))

    with pytest.raises(InvalidSettingsError):
        repository.load_persisted_settings_data()


def test_repository_migrates_missing_schema_version(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"paths": {"library_path": "~/custom-library.json"}}), encoding="utf-8")
    repository = FileSettingsRepository(str(settings_path))

    assert repository.load_persisted_settings_data() == {
        "schema_version": 1,
        "paths": {"library_path": "~/custom-library.json"},
    }
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "paths": {"library_path": "~/custom-library.json"},
    }
