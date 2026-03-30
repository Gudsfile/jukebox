import json

import pytest

from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService


def test_settings_service_allows_persisted_manual_name_without_selected_group(tmp_path):
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


@pytest.mark.parametrize(
    ("sonos_settings", "expected_host", "expected_name"),
    [
        (
            {
                "manual_host": "192.168.1.99",
                "selected_group": {
                    "coordinator_uid": "speaker-2",
                    "members": [
                        {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                        {"uid": "speaker-2", "name": "Office", "last_known_host": "192.168.1.40"},
                    ],
                },
            },
            "192.168.1.99",
            None,
        ),
        (
            {
                "manual_name": "Living Room",
                "selected_group": {
                    "coordinator_uid": "speaker-2",
                    "members": [
                        {"uid": "speaker-1", "name": "Kitchen", "last_known_host": "192.168.1.30"},
                        {"uid": "speaker-2", "name": "Office", "last_known_host": "192.168.1.40"},
                    ],
                },
            },
            "192.168.1.40",
            None,
        ),
        (
            {
                "manual_name": "Living Room",
                "selected_group": {
                    "coordinator_uid": "speaker-2",
                    "members": [
                        {"uid": "speaker-1", "name": "Kitchen"},
                        {"uid": "speaker-2", "name": "Office"},
                    ],
                },
            },
            None,
            "Living Room",
        ),
    ],
)
def test_settings_service_resolves_persisted_sonos_target_precedence(
    tmp_path, sonos_settings, expected_host, expected_name
):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": sonos_settings,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == expected_host
    assert runtime_config.sonos_name == expected_name


def test_settings_service_prefers_persisted_manual_host_over_selected_group(tmp_path):
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


def test_settings_service_prefers_selected_group_host_over_persisted_manual_name(tmp_path):
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

    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_name is None


def test_settings_service_falls_back_to_persisted_manual_name_when_selected_group_has_no_host(tmp_path):
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
                                    {"uid": "speaker-1", "name": "Kitchen"},
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


def test_settings_service_env_host_override_beats_persisted_selected_group(tmp_path):
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
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": "192.168.1.99", "manual_name": None, "selected_group": None}}
            }
        },
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_name is None


def test_settings_service_cli_host_override_beats_persisted_selected_group(tmp_path):
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
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        cli_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": "192.168.1.99", "manual_name": None, "selected_group": None}}
            }
        },
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_name is None


def test_settings_service_cli_host_overrides_env_name(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}),
        encoding="utf-8",
    )
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": None, "manual_name": "Living Room"}}}},
        cli_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": "192.168.1.20", "manual_name": None, "selected_group": None}}
            }
        },
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
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20", "manual_name": None}}}},
        cli_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None}}
            }
        },
    )

    runtime_config = service.resolve_jukebox_runtime()

    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Living Room"
