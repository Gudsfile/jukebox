import json
from unittest.mock import MagicMock

import pytest

from jukebox.admin.command_handlers import execute_admin_command
from jukebox.admin.commands import ApiCommand, SettingsResetCommand, SettingsSetCommand, SettingsShowCommand, UiCommand
from jukebox.settings.entities import ResolvedAdminRuntimeConfig
from jukebox.shared.dependency_messages import optional_extra_dependency_message


def test_execute_admin_command_renders_human_readable_persisted_settings():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    stdout_fn = MagicMock()

    execute_admin_command(
        verbose=False,
        command=SettingsShowCommand(type="settings_show"),
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="jukebox-admin",
        library=None,
        stdout_fn=stdout_fn,
    )

    settings_service.get_persisted_settings_view.assert_called_once_with()
    rendered_output = stdout_fn.call_args.args[0]
    assert "Persisted Settings" in rendered_output
    assert "Schema Version: 1" in rendered_output
    assert "No persisted overrides." in rendered_output


@pytest.mark.parametrize(
    ("command", "service_method", "service_args", "payload", "expected_snippets"),
    [
        (
            SettingsShowCommand(type="settings_show", effective=True),
            "get_effective_settings_view",
            (),
            {
                "settings": {
                    "paths": {"library_path": "~/.jukebox/library.json"},
                    "admin": {"api": {"port": 8000}, "ui": {"port": 8000}},
                    "jukebox": {
                        "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                        "runtime": {"loop_interval_seconds": 0.1},
                        "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
                        "player": {
                            "type": "sonos",
                            "sonos": {
                                "selected_group": {
                                    "coordinator_uid": "speaker-2",
                                    "members": [
                                        {"uid": "speaker-1", "name": "Kitchen"},
                                        {"uid": "speaker-2", "name": "Living Room"},
                                    ],
                                }
                            },
                        },
                    },
                },
                "provenance": {
                    "paths": {"library_path": "default"},
                    "admin": {"api": {"port": "file"}, "ui": {"port": "default"}},
                    "jukebox": {
                        "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                        "runtime": {"loop_interval_seconds": "default"},
                        "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                        "player": {
                            "type": "file",
                            "sonos": {"selected_group": "file"},
                        },
                    },
                },
                "derived": {
                    "paths": {
                        "expanded_library_path": "/Users/test/.jukebox/library.json",
                        "current_tag_path": "/Users/test/.jukebox/current-tag.txt",
                    }
                },
                "settings_metadata": {},
            },
            [
                "Effective Settings",
                "Paths",
                "Library Path [paths.library_path]: ~/.jukebox/library.json (source: default; restart required)",
                "Admin API Port [admin.api.port]: 8000 (source: file; restart required)",
                "Selected Sonos Group [jukebox.player.sonos.selected_group]: Living Room (coordinator); members: Kitchen, Living Room (source: file; restart required)",
                "Derived",
                "derived.paths.current_tag_path: /Users/test/.jukebox/current-tag.txt",
            ],
        ),
        (
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000"),
            "set_persisted_value",
            ("admin.api.port", "9000"),
            {
                "persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}},
                "effective": {"settings": {"admin": {"api": {"port": 9000}}}},
                "updated_paths": ["admin.api.port"],
                "restart_required": True,
                "restart_required_paths": ["admin.api.port"],
                "message": "Settings saved. Changes take effect after restart.",
            },
            [
                "Settings saved. Changes take effect after restart.",
                "Changed Paths",
                "Admin API Port [admin.api.port]",
                "Restart Required: yes",
                "Restart-Required Paths",
            ],
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.playback.pause_duration_seconds",
                value="600",
            ),
            "set_persisted_value",
            ("jukebox.playback.pause_duration_seconds", "600"),
            {"persisted": {"schema_version": 1, "jukebox": {"playback": {"pause_duration_seconds": 600}}}},
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.reader.type",
                value="nfc",
            ),
            "set_persisted_value",
            ("jukebox.reader.type", "nfc"),
            {"persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "nfc"}}}},
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.reader.nfc.read_timeout_seconds",
                value="0.2",
            ),
            "set_persisted_value",
            ("jukebox.reader.nfc.read_timeout_seconds", "0.2"),
            {"persisted": {"schema_version": 1, "jukebox": {"reader": {"nfc": {"read_timeout_seconds": 0.2}}}}},
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.player.type",
                value="sonos",
            ),
            "set_persisted_value",
            ("jukebox.player.type", "sonos"),
            {"persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}},
        ),
        (
            SettingsSetCommand(
                type="settings_set",
                dotted_path="jukebox.player.sonos.selected_group",
                value='{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"}]}',
            ),
            "set_persisted_value",
            (
                "jukebox.player.sonos.selected_group",
                '{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"}]}',
            ),
            {
                "persisted": {
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
            },
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port"),
            "reset_persisted_value",
            ("admin.ui.port",),
            {
                "persisted": {"schema_version": 1},
                "effective": {"settings": {"admin": {"ui": {"port": 8000}}}},
                "updated_paths": [],
                "restart_required": False,
                "restart_required_paths": [],
                "message": "No persisted settings changed.",
            },
            [
                "No persisted settings changed.",
                "Restart Required: no",
            ],
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="jukebox.runtime.loop_interval_seconds"),
            "reset_persisted_value",
            ("jukebox.runtime.loop_interval_seconds",),
            {"persisted": {"schema_version": 1, "jukebox": {"runtime": {}}}},
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="jukebox.reader.nfc.read_timeout_seconds"),
            "reset_persisted_value",
            ("jukebox.reader.nfc.read_timeout_seconds",),
            {"persisted": {"schema_version": 1, "jukebox": {"reader": {"nfc": {}}}}},
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="jukebox.player.sonos.selected_group"),
            "reset_persisted_value",
            ("jukebox.player.sonos.selected_group",),
            {"persisted": {"schema_version": 1, "jukebox": {"player": {"sonos": {}}}}},
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="admin"),
            "reset_persisted_value",
            ("admin",),
            {"persisted": {"schema_version": 1}},
        ),
    ],
)
def test_execute_admin_command_renders_human_readable_settings_output(
    command,
    service_method,
    service_args,
    payload,
    expected_snippets,
):
    settings_service = MagicMock()
    getattr(settings_service, service_method).return_value = payload
    stdout_fn = MagicMock()

    execute_admin_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="jukebox-admin",
        library=None,
        stdout_fn=stdout_fn,
    )

    getattr(settings_service, service_method).assert_called_once_with(*service_args)
    rendered_output = stdout_fn.call_args.args[0]
    for expected_snippet in expected_snippets:
        assert expected_snippet in rendered_output


@pytest.mark.parametrize(
    ("command", "service_method", "service_args", "payload"),
    [
        (
            SettingsShowCommand(type="settings_show", effective=True, json_output=True),
            "get_effective_settings_view",
            (),
            {"settings": {"admin": {"api": {"port": 8000}}}},
        ),
        (
            SettingsSetCommand(type="settings_set", dotted_path="admin.api.port", value="9000", json_output=True),
            "set_persisted_value",
            ("admin.api.port", "9000"),
            {"persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}},
        ),
        (
            SettingsResetCommand(type="settings_reset", dotted_path="admin.ui.port", json_output=True),
            "reset_persisted_value",
            ("admin.ui.port",),
            {"persisted": {"schema_version": 1, "admin": {}}},
        ),
    ],
)
def test_execute_admin_command_preserves_json_payloads_in_json_mode(command, service_method, service_args, payload):
    settings_service = MagicMock()
    getattr(settings_service, service_method).return_value = payload
    stdout_fn = MagicMock()

    execute_admin_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="jukebox-admin",
        library=None,
        stdout_fn=stdout_fn,
    )

    getattr(settings_service, service_method).assert_called_once_with(*service_args)
    stdout_fn.assert_called_once_with(json.dumps(payload, indent=2))


def test_execute_admin_command_writes_discstore_settings_deprecation_warning_to_stderr():
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {
        "settings": {
            "paths": {"library_path": "~/.jukebox/library.json"},
            "admin": {"api": {"port": 8000}, "ui": {"port": 8000}},
            "jukebox": {
                "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                "runtime": {"loop_interval_seconds": 0.1},
                "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
                "player": {"type": "dryrun", "sonos": {"selected_group": None}},
            },
        },
        "provenance": {
            "paths": {"library_path": "default"},
            "admin": {"api": {"port": "default"}, "ui": {"port": "default"}},
            "jukebox": {
                "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                "runtime": {"loop_interval_seconds": "default"},
                "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                "player": {"type": "default", "sonos": {"selected_group": "default"}},
            },
        },
        "derived": {
            "paths": {"expanded_library_path": "/tmp/library.json", "current_tag_path": "/tmp/current-tag.txt"}
        },
        "settings_metadata": {},
    }
    stdout_fn = MagicMock()
    stderr_fn = MagicMock()
    command = SettingsShowCommand(type="settings_show", effective=True, json_output=True)

    execute_admin_command(
        verbose=False,
        command=command,
        settings_service=settings_service,
        build_api_app=MagicMock(),
        build_ui_app=MagicMock(),
        source_command="discstore",
        library="/tmp/custom library.json",
        stdout_fn=stdout_fn,
        stderr_fn=stderr_fn,
    )

    stderr_message = stderr_fn.call_args.args[0]
    assert "deprecated" in stderr_message
    assert "`jukebox-admin --library '/tmp/custom library.json' settings show --effective --json`" in stderr_message
    stdout_fn.assert_called_once()


@pytest.mark.parametrize(
    ("command", "builder_name", "expected_port"),
    [
        (ApiCommand(type="api", port=1111), "build_api_app", 7777),
        (UiCommand(type="ui", port=2222), "build_ui_app", 8888),
    ],
)
def test_execute_admin_command_starts_server_with_resolved_runtime(mocker, command, builder_name, expected_port):
    mock_uvicorn = mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})["uvicorn"]
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=7777,
        ui_port=8888,
        verbose=True,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    fake_app = MagicMock(app=MagicMock(name="server_app"))
    build_api_app = MagicMock(return_value=fake_app)
    build_ui_app = MagicMock(return_value=fake_app)

    execute_admin_command(
        verbose=True,
        command=command,
        settings_service=settings_service,
        build_api_app=build_api_app,
        build_ui_app=build_ui_app,
        source_command="jukebox-admin",
        library=None,
    )

    settings_service.resolve_admin_runtime.assert_called_once_with(verbose=True)
    if builder_name == "build_api_app":
        build_api_app.assert_called_once_with("/resolved/library.json", settings_service)
        build_ui_app.assert_not_called()
    else:
        build_ui_app.assert_called_once_with("/resolved/library.json", settings_service)
        build_api_app.assert_not_called()
    mock_uvicorn.run.assert_called_once_with(fake_app.app, host="0.0.0.0", port=expected_port)


@pytest.mark.parametrize(
    ("command", "extra_name"),
    [
        (ApiCommand(type="api", port=1234), "api"),
        (UiCommand(type="ui", port=1234), "ui"),
    ],
)
def test_execute_admin_command_reports_missing_optional_dependencies(mocker, command, extra_name):
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
    mocker.patch(
        "jukebox.admin.command_handlers.import_module",
        side_effect=ModuleNotFoundError("No module named 'uvicorn'"),
    )

    with pytest.raises(SystemExit) as err:
        execute_admin_command(
            verbose=False,
            command=command,
            settings_service=settings_service,
            build_api_app=MagicMock(),
            build_ui_app=MagicMock(),
            source_command="jukebox-admin",
            library=None,
        )

    assert f"`jukebox-admin {extra_name}` requires the optional `{extra_name}` dependencies." in str(err.value)


@pytest.mark.parametrize(
    ("command", "extra_name", "builder_name"),
    [
        (ApiCommand(type="api", port=1234), "api", "build_api_app"),
        (UiCommand(type="ui", port=1234), "ui", "build_ui_app"),
    ],
)
def test_execute_admin_command_rewrites_controller_dependency_failures(mocker, command, extra_name, builder_name):
    runtime_config = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
    settings_service = MagicMock()
    settings_service.resolve_admin_runtime.return_value = runtime_config
    mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})
    build_api_app = MagicMock()
    build_ui_app = MagicMock()
    target_builder = build_api_app if builder_name == "build_api_app" else build_ui_app
    target_builder.side_effect = ModuleNotFoundError(
        optional_extra_dependency_message(
            subject="The legacy controller module",
            extra_name=extra_name,
            source_command=f"discstore {extra_name}",
        )
    )

    with pytest.raises(SystemExit) as err:
        execute_admin_command(
            verbose=False,
            command=command,
            settings_service=settings_service,
            build_api_app=build_api_app,
            build_ui_app=build_ui_app,
            source_command="jukebox-admin",
        )

    assert str(err.value) == optional_extra_dependency_message(
        subject=f"`jukebox-admin {extra_name}`",
        extra_name=extra_name,
        source_command=f"jukebox-admin {extra_name}",
    )
