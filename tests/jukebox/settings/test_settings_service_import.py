import json
from pathlib import Path

import pytest

from jukebox.settings.errors import InvalidSettingsError, UnsupportedSettingsVersionError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService
from jukebox.settings.types import JsonObject


def build_service(tmp_path: Path, persisted: JsonObject | None = None) -> tuple[SettingsService, Path]:
    settings_path = tmp_path / "settings.json"
    if persisted is not None:
        settings_path.write_text(json.dumps(persisted), encoding="utf-8")
    return SettingsService(repository=FileSettingsRepository(str(settings_path))), settings_path


def test_preview_settings_import_lists_changed_paths_without_writing(tmp_path):
    persisted: JsonObject = {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
        "paths": {"library_path": "/old.json"},
    }
    service, settings_path = build_service(tmp_path, persisted)

    preview = service.preview_settings_import(
        {"schema_version": 1, "admin": {"api": {"port": 8100}, "ui": {"port": 8200}}, "jukebox": {}}
    )

    assert preview == {
        "updated_paths": ["admin.ui.port", "paths.library_path"],
        "restart_required_paths": ["admin.ui.port", "paths.library_path"],
        "current_settings_error": None,
    }
    assert json.loads(settings_path.read_text(encoding="utf-8")) == persisted


def test_preview_settings_import_treats_selected_group_as_one_path(tmp_path):
    service, _ = build_service(tmp_path)

    preview = service.preview_settings_import(
        {
            "schema_version": 1,
            "jukebox": {
                "player": {
                    "sonos": {"selected_group": {"coordinator_uid": "speaker-1", "members": [{"uid": "speaker-1"}]}}
                }
            },
        }
    )

    assert preview["updated_paths"] == ["jukebox.player.sonos.selected_group"]


def test_preview_settings_import_compares_against_empty_settings_when_current_file_is_invalid(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not json", encoding="utf-8")
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    preview = service.preview_settings_import({"schema_version": 1, "admin": {"api": {"port": 8100}}})

    assert preview["updated_paths"] == ["admin.api.port"]
    assert "Malformed settings file" in str(preview["current_settings_error"])


def test_import_persisted_settings_replaces_the_whole_file(tmp_path):
    service, settings_path = build_service(
        tmp_path, {"schema_version": 1, "admin": {"api": {"port": 8100}, "ui": {"port": 8200}}}
    )
    imported: JsonObject = {"schema_version": 1, "paths": {"library_path": "/new.json"}}

    result = service.import_persisted_settings(imported)

    assert json.loads(settings_path.read_text(encoding="utf-8")) == imported
    assert result["updated_paths"] == ["admin.api.port", "admin.ui.port", "paths.library_path"]
    assert result["restart_required"] is True
    assert result["message"] == "Settings imported. Changes take effect after restart."


def test_import_persisted_settings_writes_migrated_data(tmp_path):
    service, settings_path = build_service(tmp_path)

    service.import_persisted_settings({"admin": {"api": {"port": 8100}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "admin": {"api": {"port": 8100}},
        "schema_version": 1,
    }


def test_import_persisted_settings_replaces_an_invalid_current_file(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not json", encoding="utf-8")
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    service.import_persisted_settings({"schema_version": 1})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {"schema_version": 1}


def test_import_persisted_settings_writes_numbers_given_as_strings_as_numbers(tmp_path):
    service, settings_path = build_service(tmp_path)

    service.import_persisted_settings(
        {
            "schema_version": 1,
            "jukebox": {"runtime": {"loop_interval_seconds": "0.1"}},
            "admin": {"api": {"port": "8100"}},
        }
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {"runtime": {"loop_interval_seconds": 0.1}},
        "admin": {"api": {"port": 8100}},
    }


@pytest.mark.parametrize(
    "raw_data,error_type,message",
    [
        pytest.param([], InvalidSettingsError, "root must be a JSON object", id="not_an_object"),
        pytest.param(
            {"schema_version": "1"}, InvalidSettingsError, "schema_version must be an integer", id="version_type"
        ),
        pytest.param(
            {"schema_version": 99},
            UnsupportedSettingsVersionError,
            "Unsupported settings schema_version 99",
            id="future",
        ),
        pytest.param(
            {"schema_version": 1, "unknown": True}, InvalidSettingsError, "Invalid settings file", id="unknown_key"
        ),
        pytest.param(
            {"schema_version": 1, "admin": {"api": {"port": "eighty"}}},
            InvalidSettingsError,
            "Invalid settings file",
            id="invalid_value",
        ),
        pytest.param(
            {
                "schema_version": 1,
                "jukebox": {"runtime": {"loop_interval_seconds": 1}, "playback": {"pause_delay_seconds": 0.5}},
            },
            InvalidSettingsError,
            "loop_interval_seconds must be lower than",
            id="cross_field_rule",
        ),
        pytest.param(
            {
                "schema_version": 1,
                # Compared with the float default of pause_delay_seconds.
                "jukebox": {"runtime": {"loop_interval_seconds": "1"}},
            },
            InvalidSettingsError,
            "loop_interval_seconds must be lower than",
            id="cross_field_rule_with_numbers_as_strings",
        ),
    ],
)
def test_invalid_settings_import_is_rejected_and_nothing_is_written(tmp_path, raw_data, error_type, message):
    persisted: JsonObject = {"schema_version": 1, "admin": {"api": {"port": 8100}}}
    service, settings_path = build_service(tmp_path, persisted)

    with pytest.raises(error_type, match=message):
        service.preview_settings_import(raw_data)
    with pytest.raises(error_type, match=message):
        service.import_persisted_settings(raw_data)

    assert json.loads(settings_path.read_text(encoding="utf-8")) == persisted
