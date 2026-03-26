import json
import os
from typing import cast
from unittest.mock import MagicMock

import pytest

from jukebox.settings.errors import InvalidSettingsError, MalformedSettingsFileError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService, build_environment_settings_overrides
from jukebox.settings.types import JsonObject, JsonValue
from jukebox.shared.config_utils import get_current_tag_path


def _lookup_json_value(root: JsonObject, *path: str) -> JsonValue:
    current: JsonValue = root

    for part in path:
        assert isinstance(current, dict)
        current = current[part]

    return current


def _lookup_json_object(root: JsonObject, *path: str) -> JsonObject:
    value = _lookup_json_value(root, *path)
    assert isinstance(value, dict)
    return cast(JsonObject, value)


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


def test_settings_service_builds_effective_view_with_provenance(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "paths": {"library_path": "~/file-library.json"},
                "admin": {"api": {"port": 8100}},
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"paths": {"library_path": "/env/library.json"}},
        cli_overrides={"admin": {"ui": {"port": 8200}}},
    )

    effective_view = service.get_effective_settings_view()

    assert _lookup_json_value(effective_view, "settings", "paths", "library_path") == "/env/library.json"
    assert _lookup_json_value(effective_view, "settings", "admin", "api", "port") == 8100
    assert _lookup_json_value(effective_view, "settings", "admin", "ui", "port") == 8200
    assert _lookup_json_value(effective_view, "provenance", "paths", "library_path") == "env"
    assert _lookup_json_value(effective_view, "provenance", "admin", "api", "port") == "file"
    assert _lookup_json_value(effective_view, "provenance", "admin", "ui", "port") == "cli"
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "runtime", "loop_interval_seconds") == "default"
    assert _lookup_json_value(effective_view, "settings_metadata", "admin", "api", "port", "requires_restart") is True
    assert (
        _lookup_json_value(
            effective_view, "settings_metadata", "jukebox", "runtime", "loop_interval_seconds", "requires_restart"
        )
        is True
    )


def test_settings_service_set_persisted_value_updates_sparse_settings_and_reports_restart(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value("admin.api.port", "8100")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }
    effective_view = _lookup_json_object(result, "effective")
    assert _lookup_json_value(effective_view, "settings", "admin", "api", "port") == 8100
    assert result["updated_paths"] == ["admin.api.port"]
    assert result["restart_required"] is True
    assert result["restart_required_paths"] == ["admin.api.port"]
    assert result["message"] == "Settings saved. Changes take effect after restart."


def test_settings_service_set_library_path_allows_unrelated_invalid_timing_state(tmp_path):
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

    result = service.set_persisted_value("paths.library_path", "~/repaired-library.json")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "paths": {"library_path": "~/repaired-library.json"},
        "jukebox": {
            "playback": {"pause_delay_seconds": 0.3},
            "runtime": {"loop_interval_seconds": 0.3},
        },
    }
    assert result["updated_paths"] == ["paths.library_path"]
    effective_view = _lookup_json_object(result, "effective")
    assert _lookup_json_value(effective_view, "settings", "paths", "library_path") == "~/repaired-library.json"
    runtime_config = service.resolve_admin_runtime()
    assert runtime_config.library_path == os.path.abspath(os.path.expanduser("~/repaired-library.json"))


def test_settings_service_reset_removes_only_requested_override(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "admin": {
                    "api": {"port": 8100},
                    "ui": {"port": 8200},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("admin.api.port")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"ui": {"port": 8200}},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {"ui": {"port": 8200}},
    }
    runtime_config = service.resolve_admin_runtime()
    assert runtime_config.api_port == 8000
    assert runtime_config.ui_port == 8200


def test_settings_service_reset_removes_section_subtree(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "paths": {"library_path": "~/custom-library.json"},
                "admin": {
                    "api": {"port": 8100},
                    "ui": {"port": 8200},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("admin")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "paths": {"library_path": "~/custom-library.json"},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "paths": {"library_path": "~/custom-library.json"},
    }
    assert result["updated_paths"] == ["admin.api.port", "admin.ui.port"]
    assert result["restart_required_paths"] == ["admin.api.port", "admin.ui.port"]
    runtime_config = service.resolve_admin_runtime()
    assert runtime_config.api_port == 8000
    assert runtime_config.ui_port == 8000


def test_settings_service_reset_jukebox_resets_reader_and_timing_settings_but_preserves_player_settings(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {"manual_host": "192.168.1.20"},
                    },
                    "reader": {
                        "type": "nfc",
                        "nfc": {"read_timeout_seconds": 0.2},
                    },
                    "playback": {
                        "pause_duration_seconds": 600,
                        "pause_delay_seconds": 0.3,
                    },
                    "runtime": {"loop_interval_seconds": 0.2},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("jukebox")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": "192.168.1.20"},
            },
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {"manual_host": "192.168.1.20"},
            },
        },
    }
    assert result["updated_paths"] == [
        "jukebox.playback.pause_delay_seconds",
        "jukebox.playback.pause_duration_seconds",
        "jukebox.reader.nfc.read_timeout_seconds",
        "jukebox.reader.type",
        "jukebox.runtime.loop_interval_seconds",
    ]
    runtime_config = service.resolve_jukebox_runtime()
    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.reader_type == "dryrun"
    assert runtime_config.pause_duration_seconds == 900
    assert runtime_config.pause_delay_seconds == 0.25
    assert runtime_config.loop_interval_seconds == 0.1
    assert runtime_config.nfc_read_timeout_seconds == 0.1


def test_settings_service_patch_updates_library_path_and_derived_current_tag_path(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings(
        {
            "paths": {"library_path": "~/music/library.json"},
            "admin": {"ui": {"port": 8200}},
        }
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "paths": {"library_path": "~/music/library.json"},
        "admin": {"ui": {"port": 8200}},
    }
    effective_view = _lookup_json_object(result, "effective")
    assert _lookup_json_value(effective_view, "settings", "paths", "library_path") == "~/music/library.json"
    assert _lookup_json_value(effective_view, "derived", "paths", "current_tag_path") == get_current_tag_path(
        "~/music/library.json"
    )
    assert result["updated_paths"] == ["admin.ui.port", "paths.library_path"]
    assert result["restart_required_paths"] == ["admin.ui.port", "paths.library_path"]


def test_settings_service_set_to_default_persists_explicit_pin(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value("admin.api.port", "8000")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["updated_paths"] == ["admin.api.port"]
    assert result["restart_required"] is True
    assert result["restart_required_paths"] == ["admin.api.port"]
    assert result["message"] == "Settings saved. Changes take effect after restart."


def test_settings_service_reset_non_persisted_value_is_noop_and_does_not_create_file(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("admin.api.port")

    assert not settings_path.exists()
    assert result["persisted"] == {"schema_version": 1}
    assert result["updated_paths"] == []
    assert result["restart_required"] is False
    assert result["restart_required_paths"] == []
    assert result["message"] == "No persisted settings changed."


def test_settings_service_patch_default_value_persists_explicit_pin(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings({"admin": {"api": {"port": 8000}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["updated_paths"] == ["admin.api.port"]
    assert result["restart_required"] is True
    assert result["restart_required_paths"] == ["admin.api.port"]
    assert result["message"] == "Settings saved. Changes take effect after restart."


def test_settings_service_reset_preserves_unrelated_explicit_default_pins(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "admin": {
                    "api": {"port": 8000},
                    "ui": {"port": 8200},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("admin.ui.port")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {"api": {"port": 8000}},
    }
    assert result["updated_paths"] == ["admin.ui.port"]
    runtime_config = service.resolve_admin_runtime()
    assert runtime_config.api_port == 8000
    assert runtime_config.ui_port == 8000


def test_settings_service_patch_preserves_unrelated_explicit_default_pins(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "admin": {
                    "api": {"port": 8000},
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings({"admin": {"ui": {"port": 8200}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {
            "api": {"port": 8000},
            "ui": {"port": 8200},
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {
            "api": {"port": 8000},
            "ui": {"port": 8200},
        },
    }
    assert result["updated_paths"] == ["admin.ui.port"]


def test_settings_service_reset_section_preserves_non_editable_persisted_values(tmp_path, monkeypatch):
    import jukebox.settings.definitions as definitions

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "admin": {
                    "api": {"port": 8100},
                    "ui": {"port": 8200},
                },
            }
        ),
        encoding="utf-8",
    )
    restricted_metadata = {key: value for key, value in definitions.SETTINGS.items() if key != "admin.ui.port"}
    monkeypatch.setattr(definitions, "SETTINGS", restricted_metadata)
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("admin")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {
            "ui": {"port": 8200},
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "admin": {
            "ui": {"port": 8200},
        },
    }
    assert result["updated_paths"] == ["admin.api.port"]
    runtime_config = service.resolve_admin_runtime()
    assert runtime_config.api_port == 8000
    assert runtime_config.ui_port == 8200


def test_settings_service_set_rejects_unsupported_path_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Unsupported settings path for write"):
        service.set_persisted_value("admin.api.host", "localhost")

    assert not settings_path.exists()


def test_settings_service_patch_updates_playback_timing_settings_and_reports_restart(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings(
        {
            "jukebox": {
                "playback": {
                    "pause_duration_seconds": 600,
                    "pause_delay_seconds": 0.3,
                },
                "runtime": {
                    "loop_interval_seconds": 0.2,
                },
            }
        }
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {
                "pause_duration_seconds": 600,
                "pause_delay_seconds": 0.3,
            },
            "runtime": {
                "loop_interval_seconds": 0.2,
            },
        },
    }
    effective_view = _lookup_json_object(result, "effective")

    assert _lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_duration_seconds") == 600
    assert _lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_delay_seconds") == 0.3
    assert _lookup_json_value(effective_view, "settings", "jukebox", "runtime", "loop_interval_seconds") == 0.2
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "playback", "pause_duration_seconds") == "file"
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "playback", "pause_delay_seconds") == "file"
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "runtime", "loop_interval_seconds") == "file"
    assert result["updated_paths"] == [
        "jukebox.playback.pause_delay_seconds",
        "jukebox.playback.pause_duration_seconds",
        "jukebox.runtime.loop_interval_seconds",
    ]
    assert result["restart_required"] is True
    assert result["restart_required_paths"] == [
        "jukebox.playback.pause_delay_seconds",
        "jukebox.playback.pause_duration_seconds",
        "jukebox.runtime.loop_interval_seconds",
    ]
    assert result["message"] == "Settings saved. Changes take effect after restart."


def test_settings_service_patch_updates_reader_settings_and_reports_restart(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings(
        {
            "jukebox": {
                "reader": {
                    "type": "nfc",
                    "nfc": {"read_timeout_seconds": 0.2},
                }
            }
        }
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "reader": {
                "type": "nfc",
                "nfc": {"read_timeout_seconds": 0.2},
            }
        },
    }
    effective_view = _lookup_json_object(result, "effective")
    assert _lookup_json_value(effective_view, "settings", "jukebox", "reader", "type") == "nfc"
    assert _lookup_json_value(effective_view, "settings", "jukebox", "reader", "nfc", "read_timeout_seconds") == 0.2
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "reader", "type") == "file"
    assert (
        _lookup_json_value(
            effective_view,
            "provenance",
            "jukebox",
            "reader",
            "nfc",
            "read_timeout_seconds",
        )
        == "file"
    )
    assert _lookup_json_value(effective_view, "change_metadata", "jukebox", "reader", "type", "section") == "reader"
    assert (
        _lookup_json_value(
            effective_view,
            "change_metadata",
            "jukebox",
            "reader",
            "nfc",
            "read_timeout_seconds",
            "requires_restart",
        )
        is True
    )
    assert result["updated_paths"] == [
        "jukebox.reader.nfc.read_timeout_seconds",
        "jukebox.reader.type",
    ]
    assert result["restart_required_paths"] == [
        "jukebox.reader.nfc.read_timeout_seconds",
        "jukebox.reader.type",
    ]
    assert result["message"] == "Settings saved. Changes take effect after restart."

    runtime_config = service.resolve_jukebox_runtime()
    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.2


def test_settings_service_reset_removes_only_requested_timing_override(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "playback": {
                        "pause_duration_seconds": 600,
                        "pause_delay_seconds": 0.3,
                    },
                    "runtime": {
                        "loop_interval_seconds": 0.2,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("jukebox.playback.pause_delay_seconds")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "playback": {
                "pause_duration_seconds": 600,
            },
            "runtime": {
                "loop_interval_seconds": 0.2,
            },
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "jukebox": {
            "playback": {
                "pause_duration_seconds": 600,
            },
            "runtime": {
                "loop_interval_seconds": 0.2,
            },
        },
    }
    assert result["updated_paths"] == ["jukebox.playback.pause_delay_seconds"]
    assert result["restart_required_paths"] == ["jukebox.playback.pause_delay_seconds"]
    runtime_config = service.resolve_jukebox_runtime()
    assert runtime_config.pause_duration_seconds == 600
    assert runtime_config.pause_delay_seconds == 0.25
    assert runtime_config.loop_interval_seconds == 0.2


def test_settings_service_reset_removes_only_requested_reader_override(tmp_path):
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

    result = service.reset_persisted_value("jukebox.reader.nfc.read_timeout_seconds")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "reader": {
                "type": "nfc",
            }
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "jukebox": {
            "reader": {
                "type": "nfc",
            }
        },
    }
    assert result["updated_paths"] == ["jukebox.reader.nfc.read_timeout_seconds"]
    assert result["restart_required_paths"] == ["jukebox.reader.nfc.read_timeout_seconds"]
    runtime_config = service.resolve_jukebox_runtime()
    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.1


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
                "nfc": {"read_timeout_seconds": 0.2},
            }
        },
    }
    assert dryrun_result["updated_paths"] == ["jukebox.reader.type"]

    runtime_config = service.resolve_jukebox_runtime()
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
    runtime_config = service.resolve_jukebox_runtime()
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


def test_build_environment_settings_overrides_reads_current_env_vars():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_LIBRARY_PATH", "/env/library.json")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/env/library.json"},
        "jukebox": {"player": {"sonos": {"manual_name": "Living Room"}}},
    }
    warning.assert_not_called()


def test_build_environment_settings_overrides_reads_deprecated_env_vars_with_warning():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("LIBRARY_PATH", "/deprecated/library.json")
        monkeypatch.setenv("SONOS_HOST", "192.168.1.20")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/deprecated/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20"}}},
    }
    warning.assert_any_call("The LIBRARY_PATH environment variable is deprecated, use JUKEBOX_LIBRARY_PATH instead.")
    warning.assert_any_call("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    assert warning.call_count == 2


def test_build_environment_settings_overrides_prefers_current_env_vars_over_deprecated():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_LIBRARY_PATH", "/current/library.json")
        monkeypatch.setenv("LIBRARY_PATH", "/deprecated/library.json")
        monkeypatch.setenv("JUKEBOX_SONOS_HOST", "192.168.1.10")
        monkeypatch.setenv("SONOS_HOST", "192.168.1.20")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/current/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": "192.168.1.10"}}},
    }
    warning.assert_any_call("The LIBRARY_PATH environment variable is deprecated, use JUKEBOX_LIBRARY_PATH instead.")
    warning.assert_any_call("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    assert warning.call_count == 2


def test_settings_service_allows_sonos_discovery_without_manual_target(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name is None


def test_settings_service_allows_admin_runtime_resolution_without_sonos_target(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_admin_runtime()

    assert runtime_config.library_path == os.path.abspath(os.path.expanduser("~/.jukebox/library.json"))
    assert runtime_config.api_port == 8000
    assert runtime_config.ui_port == 8000


def test_settings_service_builds_effective_view_without_sonos_target(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    effective_view = service.get_effective_settings_view()

    assert _lookup_json_value(effective_view, "settings", "jukebox", "player", "type") == "sonos"
    assert _lookup_json_value(effective_view, "settings", "jukebox", "player", "sonos", "manual_host") is None
    assert _lookup_json_value(effective_view, "settings", "jukebox", "player", "sonos", "manual_name") is None
    assert _lookup_json_value(effective_view, "provenance", "jukebox", "player", "type") == "file"


def test_settings_service_allows_env_override_to_supply_sonos_target(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20"}}}},
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.sonos_name is None


def test_settings_service_prefers_manual_host_over_selected_group(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "manual_host": "192.168.1.99",
                            "selected_group": {
                                "coordinator_uid": "speaker-2",
                                "members": [
                                    {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                                    {"uid": "speaker-2", "name": "Living Room", "last_known_host": "192.168.1.40"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_name is None


def test_settings_service_prefers_manual_name_over_selected_group(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "manual_name": "Living Room",
                            "selected_group": {
                                "coordinator_uid": "speaker-2",
                                "members": [
                                    {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                                    {"uid": "speaker-2", "name": "Office", "last_known_host": "192.168.1.40"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Living Room"


def test_settings_service_prefers_selected_group_coordinator_host_when_no_manual_override(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "speaker-2",
                                "members": [
                                    {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                                    {"uid": "speaker-2", "name": "Living Room", "last_known_host": "192.168.1.40"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_name is None


def test_settings_service_falls_back_to_any_selected_group_host_when_no_manual_override(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "speaker-2",
                                "members": [
                                    {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                                    {"uid": "speaker-2", "name": "Living Room"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.30"
    assert runtime_config.sonos_name is None


def test_settings_service_cli_host_overrides_env_name(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_name": "Living Room"}}}},
        cli_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20", "manual_name": None}}}},
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.sonos_name is None


def test_settings_service_allows_env_override_to_supply_sonos_name(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_name": "Living Room"}}}},
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Living Room"


def test_settings_service_cli_name_overrides_env_host(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20"}}}},
        cli_overrides={"jukebox": {"player": {"sonos": {"manual_host": None, "manual_name": "Living Room"}}}},
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Living Room"


def test_settings_service_rejects_manual_host_and_name_together(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20", "manual_name": "Living Room"}}}},
    )

    with pytest.raises(InvalidSettingsError):
        service.resolve_jukebox_runtime()


def test_settings_service_rejects_pause_delay_below_minimum_after_cli_overrides(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        cli_overrides={"jukebox": {"playback": {"pause_delay_seconds": 0.19}}},
    )

    with pytest.raises(InvalidSettingsError):
        service.resolve_jukebox_runtime()


def test_settings_service_allows_effective_settings_view_with_invalid_timing_relationships(tmp_path):
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

    effective_view = service.get_effective_settings_view()

    assert _lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_delay_seconds") == 0.3
    assert _lookup_json_value(effective_view, "settings", "jukebox", "runtime", "loop_interval_seconds") == 0.3


def test_settings_service_rejects_loop_interval_not_lower_than_pause_delay_at_runtime(tmp_path):
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

    with pytest.raises(
        InvalidSettingsError,
        match="loop_interval_seconds must be lower than jukebox.playback.pause_delay_seconds",
    ):
        service.resolve_jukebox_runtime()
