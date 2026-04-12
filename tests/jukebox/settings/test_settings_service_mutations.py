import json
import os

import pytest

from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService
from jukebox.shared.config_utils import get_current_tag_path
from tests.jukebox.settings._helpers import (
    StubSonosService,
    build_resolved_sonos_group_runtime,
    lookup_json_object,
    lookup_json_value,
    resolve_jukebox_runtime,
)


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

    assert lookup_json_value(effective_view, "settings", "paths", "library_path") == "/env/library.json"
    assert lookup_json_value(effective_view, "settings", "admin", "api", "port") == 8100
    assert lookup_json_value(effective_view, "settings", "admin", "ui", "port") == 8200
    assert lookup_json_value(effective_view, "provenance", "paths", "library_path") == "env"
    assert lookup_json_value(effective_view, "provenance", "admin", "api", "port") == "file"
    assert lookup_json_value(effective_view, "provenance", "admin", "ui", "port") == "cli"
    assert lookup_json_value(effective_view, "provenance", "jukebox", "runtime", "loop_interval_seconds") == "default"
    assert lookup_json_value(effective_view, "settings_metadata", "admin", "api", "port", "requires_restart") is True
    assert (
        lookup_json_value(
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
    effective_view = lookup_json_object(result, "effective")
    assert lookup_json_value(effective_view, "settings", "admin", "api", "port") == 8100
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
    effective_view = lookup_json_object(result, "effective")
    assert lookup_json_value(effective_view, "settings", "paths", "library_path") == "~/repaired-library.json"
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


def test_settings_service_reset_jukebox_resets_editable_player_reader_and_timing_settings(tmp_path):
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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
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

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {"schema_version": 1}
    assert result["persisted"] == {"schema_version": 1}
    assert result["updated_paths"] == [
        "jukebox.playback.pause_delay_seconds",
        "jukebox.playback.pause_duration_seconds",
        "jukebox.player.sonos.selected_group",
        "jukebox.player.type",
        "jukebox.reader.nfc.read_timeout_seconds",
        "jukebox.reader.type",
        "jukebox.runtime.loop_interval_seconds",
    ]
    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.player_type == "dryrun"
    assert runtime_config.sonos_host is None
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
    effective_view = lookup_json_object(result, "effective")
    assert lookup_json_value(effective_view, "settings", "paths", "library_path") == "~/music/library.json"
    assert lookup_json_value(effective_view, "derived", "paths", "current_tag_path") == get_current_tag_path(
        "~/music/library.json"
    )
    assert result["updated_paths"] == ["admin.ui.port", "paths.library_path"]
    assert result["restart_required_paths"] == ["admin.ui.port", "paths.library_path"]


def test_settings_service_set_to_default_persists_explicit_value(tmp_path):
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


def test_settings_service_patch_default_value_persists_explicit_value(tmp_path):
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
    effective_view = lookup_json_object(result, "effective")

    assert lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_duration_seconds") == 600
    assert lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_delay_seconds") == 0.3
    assert lookup_json_value(effective_view, "settings", "jukebox", "runtime", "loop_interval_seconds") == 0.2
    assert lookup_json_value(effective_view, "provenance", "jukebox", "playback", "pause_duration_seconds") == "file"
    assert lookup_json_value(effective_view, "provenance", "jukebox", "playback", "pause_delay_seconds") == "file"
    assert lookup_json_value(effective_view, "provenance", "jukebox", "runtime", "loop_interval_seconds") == "file"
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
    effective_view = lookup_json_object(result, "effective")
    assert lookup_json_value(effective_view, "settings", "jukebox", "reader", "type") == "nfc"
    assert lookup_json_value(effective_view, "settings", "jukebox", "reader", "nfc", "read_timeout_seconds") == 0.2
    assert lookup_json_value(effective_view, "provenance", "jukebox", "reader", "type") == "file"
    assert (
        lookup_json_value(
            effective_view,
            "provenance",
            "jukebox",
            "reader",
            "nfc",
            "read_timeout_seconds",
        )
        == "file"
    )
    assert lookup_json_value(effective_view, "settings_metadata", "jukebox", "reader", "type", "section") == "reader"
    assert (
        lookup_json_value(
            effective_view,
            "settings_metadata",
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

    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.2


def test_settings_service_set_selected_group_from_json_string(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value(
        "jukebox.player.sonos.selected_group",
        '{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"}]}',
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}],
                    }
                }
            }
        },
    }
    assert result["updated_paths"] == ["jukebox.player.sonos.selected_group"]
    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.player_type == "dryrun"
    assert runtime_config.sonos_host is None


def test_settings_service_patch_updates_player_settings_and_reports_restart(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings(
        {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-1",
                            "members": [{"uid": "speaker-1"}],
                        }
                    },
                }
            }
        }
    )

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "type": "sonos",
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}],
                    }
                },
            }
        },
    }
    effective_view = lookup_json_object(result, "effective")
    assert lookup_json_value(effective_view, "settings", "jukebox", "player", "type") == "sonos"
    assert (
        lookup_json_value(
            effective_view,
            "settings",
            "jukebox",
            "player",
            "sonos",
            "selected_group",
            "coordinator_uid",
        )
        == "speaker-1"
    )
    assert lookup_json_value(effective_view, "provenance", "jukebox", "player", "type") == "file"
    assert (
        lookup_json_value(
            effective_view,
            "provenance",
            "jukebox",
            "player",
            "sonos",
            "selected_group",
            "members",
        )
        == "file"
    )
    assert lookup_json_value(effective_view, "settings_metadata", "jukebox", "player", "type", "section") == "player"
    assert (
        lookup_json_value(
            effective_view,
            "settings_metadata",
            "jukebox",
            "player",
            "sonos",
            "selected_group",
            "requires_restart",
        )
        is True
    )
    assert result["updated_paths"] == [
        "jukebox.player.sonos.selected_group",
        "jukebox.player.type",
    ]
    assert result["restart_required_paths"] == [
        "jukebox.player.sonos.selected_group",
        "jukebox.player.type",
    ]
    runtime_config = resolve_jukebox_runtime(
        service,
        StubSonosService(resolved_group=build_resolved_sonos_group_runtime()),
    )
    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.sonos_group is not None


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
    runtime_config = resolve_jukebox_runtime(service)
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
    runtime_config = resolve_jukebox_runtime(service)
    assert runtime_config.reader_type == "nfc"
    assert runtime_config.nfc_read_timeout_seconds == 0.1


def test_settings_service_reset_removes_only_requested_selected_group_override(tmp_path):
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
                                "coordinator_uid": "speaker-1",
                                "members": [{"uid": "speaker-1"}],
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.reset_persisted_value("jukebox.player.sonos.selected_group")

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "type": "sonos",
            }
        },
    }
    assert result["persisted"] == {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "type": "sonos",
            }
        },
    }
    assert result["updated_paths"] == ["jukebox.player.sonos.selected_group"]
    assert result["restart_required_paths"] == ["jukebox.player.sonos.selected_group"]
