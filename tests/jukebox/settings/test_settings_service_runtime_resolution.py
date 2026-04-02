import json
import os
from unittest.mock import MagicMock

import pytest

from jukebox.settings.errors import InvalidSettingsError
from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService, build_environment_settings_overrides
from tests.jukebox.settings._helpers import lookup_json_value, resolve_jukebox_runtime


def test_settings_service_allows_sonos_runtime_without_active_target_for_autodiscovery(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = resolve_jukebox_runtime(service)

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name is None
    assert runtime_config.sonos_group is None


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

    assert lookup_json_value(effective_view, "settings", "jukebox", "player", "type") == "sonos"
    assert lookup_json_value(effective_view, "settings", "jukebox", "player", "sonos", "manual_host") is None
    assert lookup_json_value(effective_view, "settings", "jukebox", "player", "sonos", "manual_name") is None
    assert lookup_json_value(effective_view, "provenance", "jukebox", "player", "type") == "file"


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

    runtime_config = resolve_jukebox_runtime(service)

    assert runtime_config.player_type == "sonos"
    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.sonos_name is None


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
        resolve_jukebox_runtime(service)


def test_settings_service_rejects_conflicting_sonos_target_env_vars(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_SONOS_HOST", "192.168.1.20")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")
        service = SettingsService(
            repository=FileSettingsRepository(str(settings_path)),
            env_overrides=build_environment_settings_overrides(warning),
        )

    with pytest.raises(InvalidSettingsError, match="manual_host and manual_name are mutually exclusive"):
        resolve_jukebox_runtime(service)


def test_settings_service_allows_effective_view_with_selected_group_without_any_host(tmp_path):
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

    effective_view = service.get_effective_settings_view()

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


def test_settings_service_rejects_pause_delay_below_minimum_after_cli_overrides(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        cli_overrides={"jukebox": {"playback": {"pause_delay_seconds": 0.19}}},
    )

    with pytest.raises(InvalidSettingsError):
        resolve_jukebox_runtime(service)


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

    assert lookup_json_value(effective_view, "settings", "jukebox", "playback", "pause_delay_seconds") == 0.3
    assert lookup_json_value(effective_view, "settings", "jukebox", "runtime", "loop_interval_seconds") == 0.3


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
        resolve_jukebox_runtime(service)
