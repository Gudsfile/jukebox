import json

import pytest

from jukebox.settings.errors import InvalidSettingsError, MalformedSettingsFileError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsReadService


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
    service = SettingsReadService(
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


def test_settings_service_requires_sonos_target_after_merge(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsReadService(repository=FileSettingsRepository(str(settings_path)))

    with pytest.raises(InvalidSettingsError):
        service.resolve_jukebox_runtime()


def test_settings_service_allows_env_override_to_supply_sonos_target(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsReadService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20"}}}},
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.20"
