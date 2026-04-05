import json

import pytest

from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService
from tests.jukebox.settings._helpers import resolve_jukebox_runtime


def test_settings_service_set_rejects_invalid_timing_value_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Invalid settings update"):
        service.set_persisted_value("jukebox.playback.pause_delay_seconds", "0.19")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_invalid_reader_type_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Invalid settings update"):
        service.set_persisted_value("jukebox.reader.type", "serial")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_invalid_reader_timeout_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Invalid settings update"):
        service.set_persisted_value("jukebox.reader.nfc.read_timeout_seconds", "0")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_invalid_selected_group_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="selected_group.coordinator_uid must match a member uid"):
        service.set_persisted_value(
            "jukebox.player.sonos.selected_group",
            '{"coordinator_uid":"speaker-2","members":[{"uid":"speaker-1"}]}',
        )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_duplicate_selected_group_members_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="selected_group.members must not contain duplicate uids"):
        service.set_persisted_value(
            "jukebox.player.sonos.selected_group",
            '{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"},{"uid":"speaker-1"}]}',
        )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_non_json_selected_group_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="must be valid JSON"):
        service.set_persisted_value("jukebox.player.sonos.selected_group", "not-json")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_legacy_selected_group_fields_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="extra_forbidden"):
        service.set_persisted_value(
            "jukebox.player.sonos.selected_group",
            '{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1","name":"Living Room"}]}',
        )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_set_rejects_loop_interval_not_lower_than_pause_delay_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "playback": {"pause_delay_seconds": 0.3},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(
        InvalidSettingsError,
        match="loop_interval_seconds must be lower than jukebox.playback.pause_delay_seconds",
    ):
        service.set_persisted_value("jukebox.runtime.loop_interval_seconds", "0.3")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {"pause_delay_seconds": 0.3},
        },
    }


def test_settings_service_set_loop_interval_allows_unrelated_pause_duration_violation(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "playback": {"pause_duration_seconds": 10, "pause_delay_seconds": 10.0},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value("jukebox.runtime.loop_interval_seconds", "0.2")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {"pause_duration_seconds": 10, "pause_delay_seconds": 10.0},
            "runtime": {"loop_interval_seconds": 0.2},
        },
    }
    assert result["updated_paths"] == ["jukebox.runtime.loop_interval_seconds"]


def test_settings_service_patch_allows_pause_delay_greater_than_pause_duration(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "playback": {"pause_duration_seconds": 5},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings({"jukebox": {"playback": {"pause_delay_seconds": 10.0}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {"pause_duration_seconds": 5, "pause_delay_seconds": 10.0},
        },
    }
    assert result["updated_paths"] == ["jukebox.playback.pause_delay_seconds"]


def test_settings_service_set_pause_duration_allows_unrelated_loop_interval_violation(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "playback": {"pause_delay_seconds": 0.3},
                    "runtime": {"loop_interval_seconds": 0.3},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value("jukebox.playback.pause_duration_seconds", "20")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {"pause_duration_seconds": 20, "pause_delay_seconds": 0.3},
            "runtime": {"loop_interval_seconds": 0.3},
        },
    }
    assert result["updated_paths"] == ["jukebox.playback.pause_duration_seconds"]


def test_settings_service_preserves_inactive_reader_subtree_when_switching_reader_types(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "reader": {
                        "type": "nfc",
                        "nfc": {"read_timeout_seconds": 0.2},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    dryrun_result = service.set_persisted_value("jukebox.reader.type", "dryrun")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "reader": {
                "type": "dryrun",
                "nfc": {"read_timeout_seconds": 0.2},
            }
        },
    }
    assert dryrun_result["updated_paths"] == ["jukebox.reader.type"]

    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.reader_type == "dryrun"
    assert runtime_config.nfc_read_timeout_seconds == 0.2

    nfc_result = service.set_persisted_value("jukebox.reader.type", "nfc")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "reader": {
                "type": "nfc",
                "nfc": {"read_timeout_seconds": 0.2},
            }
        },
    }
    assert nfc_result["updated_paths"] == ["jukebox.reader.type"]
    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.2


def test_settings_service_patch_rejects_malformed_inactive_reader_branch_transactionally(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Unsupported settings path for write"):
        service.patch_persisted_settings({"jukebox": {"reader": {"nfc": {"unexpected": "value"}}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }
