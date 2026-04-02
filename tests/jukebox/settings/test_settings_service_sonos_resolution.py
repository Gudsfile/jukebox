import json

from jukebox.settings.file_settings_repository import FileSettingsRepository
from jukebox.settings.resolve import SettingsService
from tests.jukebox.settings._helpers import (
    StubSonosService,
    build_resolved_sonos_group_runtime,
    resolve_jukebox_runtime,
)


def test_settings_service_resolves_persisted_one_member_selected_group_into_runtime_group(tmp_path):
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
    resolved_group = build_resolved_sonos_group_runtime()
    resolver = StubSonosService(resolved_group=resolved_group)
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = resolve_jukebox_runtime(service, resolver)

    assert runtime_config.sonos_host == "192.168.1.20"
    assert runtime_config.sonos_name is None
    assert runtime_config.sonos_group == resolved_group
    assert len(resolver.calls) == 1


def test_settings_service_resolves_persisted_multi_member_selected_group_into_runtime_group(tmp_path):
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
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolved_group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = resolve_jukebox_runtime(service, StubSonosService(resolved_group=resolved_group))

    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_group == resolved_group
    assert runtime_config.sonos_group is not None
    assert [member.uid for member in runtime_config.sonos_group.members] == ["speaker-1", "speaker-2"]


def test_settings_service_allows_best_effort_selected_group_resolution_with_missing_non_coordinator(tmp_path):
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
                                    {"uid": "speaker-3"},
                                ],
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolved_group = build_resolved_sonos_group_runtime(
        coordinator_uid="speaker-2",
        speakers=[
            ("speaker-1", "Kitchen", "192.168.1.30", "household-1"),
            ("speaker-2", "Living Room", "192.168.1.40", "household-1"),
        ],
        missing_member_uids=["speaker-3"],
    )
    service = SettingsService(repository=FileSettingsRepository(str(settings_path)))

    runtime_config = resolve_jukebox_runtime(service, StubSonosService(resolved_group=resolved_group))

    assert runtime_config.sonos_host == "192.168.1.40"
    assert runtime_config.sonos_group == resolved_group
    assert runtime_config.sonos_group is not None
    assert [member.uid for member in runtime_config.sonos_group.members] == ["speaker-1", "speaker-2"]
    assert runtime_config.sonos_group.missing_member_uids == ["speaker-3"]


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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolver = StubSonosService(error=AssertionError("resolver should not be called"))
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": "192.168.1.99", "manual_name": None, "selected_group": None}}
            }
        },
    )

    runtime_config = resolve_jukebox_runtime(service, resolver)

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_group is None
    assert resolver.calls == []


def test_settings_service_env_host_override_beats_persisted_selected_group_without_clearing_it(tmp_path):
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
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolver = StubSonosService(error=AssertionError("resolver should not be called"))
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        env_overrides={"jukebox": {"player": {"sonos": {"manual_host": "192.168.1.99"}}}},
    )

    runtime_config = resolve_jukebox_runtime(service, resolver)

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_group is None
    assert resolver.calls == []


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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolver = StubSonosService(error=AssertionError("resolver should not be called"))
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        cli_overrides={
            "jukebox": {
                "player": {"sonos": {"manual_host": "192.168.1.99", "manual_name": None, "selected_group": None}}
            }
        },
    )

    runtime_config = resolve_jukebox_runtime(service, resolver)

    assert runtime_config.sonos_host == "192.168.1.99"
    assert runtime_config.sonos_group is None
    assert resolver.calls == []


def test_settings_service_cli_name_override_beats_persisted_selected_group_without_clearing_it(tmp_path):
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
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    resolver = StubSonosService(error=AssertionError("resolver should not be called"))
    service = SettingsService(
        repository=FileSettingsRepository(str(settings_path)),
        cli_overrides={"jukebox": {"player": {"sonos": {"manual_name": "Office"}}}},
    )

    runtime_config = resolve_jukebox_runtime(service, resolver)

    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Office"
    assert runtime_config.sonos_group is None
    assert resolver.calls == []


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

    runtime_config = resolve_jukebox_runtime(service)

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

    runtime_config = resolve_jukebox_runtime(service)

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

    runtime_config = resolve_jukebox_runtime(service)

    assert runtime_config.sonos_host is None
    assert runtime_config.sonos_name == "Living Room"
