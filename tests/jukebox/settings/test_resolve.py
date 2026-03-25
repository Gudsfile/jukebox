import json
import os

import pytest

from jukebox.settings.errors import InvalidSettingsError, MalformedSettingsFileError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService
from jukebox.shared.config_utils import get_current_tag_path


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

    assert effective_view["settings"]["paths"]["library_path"] == "/env/library.json"
    assert effective_view["settings"]["admin"]["api"]["port"] == 8100
    assert effective_view["settings"]["admin"]["ui"]["port"] == 8200
    assert effective_view["provenance"]["paths"]["library_path"] == "env"
    assert effective_view["provenance"]["admin"]["api"]["port"] == "file"
    assert effective_view["provenance"]["admin"]["ui"]["port"] == "cli"
    assert effective_view["provenance"]["jukebox"]["runtime"]["loop_interval_seconds"] == "default"
    assert effective_view["change_metadata"]["admin"]["api"]["port"]["requires_restart"] is True


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
    assert result["effective"]["settings"]["admin"]["api"]["port"] == 8100
    assert result["updated_paths"] == ["admin.api.port"]
    assert result["restart_required"] is True
    assert result["restart_required_paths"] == ["admin.api.port"]
    assert result["message"] == "Settings saved. Changes take effect after restart."


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
    assert result["effective"]["settings"]["paths"]["library_path"] == "~/music/library.json"
    assert result["effective"]["derived"]["paths"]["current_tag_path"] == get_current_tag_path("~/music/library.json")
    assert result["updated_paths"] == ["admin.ui.port", "paths.library_path"]
    assert result["restart_required_paths"] == ["admin.ui.port", "paths.library_path"]


def test_settings_service_set_to_default_is_noop_and_does_not_create_file(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.set_persisted_value("admin.api.port", "8000")

    assert not settings_path.exists()
    assert result["persisted"] == {"schema_version": 1}
    assert result["updated_paths"] == []
    assert result["restart_required"] is False
    assert result["restart_required_paths"] == []
    assert result["message"] == "No persisted settings changed."


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


def test_settings_service_patch_default_value_is_noop_and_does_not_create_file(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    result = service.patch_persisted_settings({"admin": {"api": {"port": 8000}}})

    assert not settings_path.exists()
    assert result["persisted"] == {"schema_version": 1}
    assert result["updated_paths"] == []
    assert result["restart_required"] is False
    assert result["restart_required_paths"] == []
    assert result["message"] == "No persisted settings changed."


def test_settings_service_set_rejects_unsupported_path_without_writing(tmp_path):
    settings_path = tmp_path / "settings.json"
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Unsupported settings path for write"):
        service.set_persisted_value("admin.api.host", "localhost")

    assert not settings_path.exists()


def test_settings_service_patch_rejects_out_of_phase_path_transactionally(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "admin": {"api": {"port": 8100}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError, match="Unsupported settings path for write"):
        service.patch_persisted_settings({"jukebox": {"runtime": {"loop_interval_seconds": 0.2}}})

    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}},
    }


def test_settings_service_requires_sonos_target_after_merge(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError):
        service.resolve_jukebox_runtime()


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

    assert effective_view["settings"]["jukebox"]["player"]["type"] == "sonos"
    assert effective_view["settings"]["jukebox"]["player"]["sonos"]["manual_host"] is None
    assert effective_view["provenance"]["jukebox"]["player"]["type"] == "file"


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
