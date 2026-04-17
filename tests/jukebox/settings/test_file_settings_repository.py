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


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("manual_host", "192.168.1.20"),
        ("manual_name", "Living Room"),
    ],
)
def test_repository_rejects_persisted_manual_sonos_targets(tmp_path, field_name, value):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "sonos": {
                            field_name: value,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    repository = FileSettingsRepository(str(settings_path))

    with pytest.raises(InvalidSettingsError):
        repository.load_persisted_settings_data()


def test_repository_rejects_legacy_selected_group_fields(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "speaker-1",
                                "members": [{"uid": "speaker-1", "name": "Living Room"}],
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    repository = FileSettingsRepository(str(settings_path))

    with pytest.raises(InvalidSettingsError):
        repository.load_persisted_settings_data()


def test_repository_accepts_selected_group_household_id(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "sonos": {
                            "selected_group": {
                                "household_id": "household-1",
                                "coordinator_uid": "speaker-1",
                                "members": [{"uid": "speaker-1"}],
                            }
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    repository = FileSettingsRepository(str(settings_path))

    assert repository.load_persisted_settings_data() == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "household_id": "household-1",
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}],
                    }
                }
            }
        },
    }


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


@pytest.mark.parametrize(
    "xdg_config_home, expected_settings_path",
    (
        ("~/.config", "/dummy/home/.config/jukebox/settings.json"),
        ("~/.config/", "/dummy/home/.config/jukebox/settings.json"),
        ("~/", "/dummy/home/jukebox/settings.json"),
        ("/custom/path", "/custom/path/jukebox/settings.json"),
    ),
)
def test_repository_uses_xdg_config_home(monkeypatch, xdg_config_home, expected_settings_path):
    monkeypatch.setenv("HOME", "/dummy/home")
    monkeypatch.setenv("XDG_CONFIG_HOME", xdg_config_home)
    repository = FileSettingsRepository()
    assert repository.filepath == expected_settings_path


def test_repository_falls_back_to_default_config_dir(monkeypatch):
    monkeypatch.setenv("HOME", "/dummy/home")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    repository = FileSettingsRepository()
    assert repository.filepath == "/dummy/home/.config/jukebox/settings.json"
