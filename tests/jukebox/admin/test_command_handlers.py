import json
from unittest.mock import MagicMock

import pytest

from jukebox.admin.command_handlers import (
    execute_server_command,
    execute_settings_command,
    execute_sonos_command,
)
from jukebox.admin.commands import (
    ApiCommand,
    SettingsResetCommand,
    SettingsSetCommand,
    SettingsShowCommand,
    SonosListCommand,
    SonosSelectCommand,
    SonosShowCommand,
    UiCommand,
)
from jukebox.admin.services import AdminServices
from jukebox.settings.entities import ResolvedAdminRuntimeConfig
from jukebox.shared.dependency_messages import optional_extra_dependency_message
from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError


def build_services():
    return AdminServices(settings=MagicMock(), sonos=MagicMock())


def test_execute_settings_command_renders_human_readable_persisted_settings():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    stdout_fn = MagicMock()

    execute_settings_command(
        command=SettingsShowCommand(type="settings_show"),
        settings_service=settings_service,
        source_command="jukebox-admin",
        stdout_fn=stdout_fn,
    )

    settings_service.get_persisted_settings_view.assert_called_once_with()
    rendered_output = stdout_fn.call_args.args[0]
    assert "Persisted Settings" in rendered_output
    assert "Schema Version: 1" in rendered_output


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
def test_execute_settings_command_preserves_json_payloads(command, service_method, service_args, payload):
    settings_service = MagicMock()
    getattr(settings_service, service_method).return_value = payload
    stdout_fn = MagicMock()

    execute_settings_command(
        command=command,
        settings_service=settings_service,
        source_command="jukebox-admin",
        stdout_fn=stdout_fn,
    )

    getattr(settings_service, service_method).assert_called_once_with(*service_args)
    stdout_fn.assert_called_once_with(json.dumps(payload, indent=2))


def test_execute_settings_command_writes_discstore_deprecation_warning_to_stderr():
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

    execute_settings_command(
        command=SettingsShowCommand(type="settings_show", effective=True, json_output=True),
        settings_service=settings_service,
        source_command="discstore",
        library="/tmp/custom library.json",
        stdout_fn=stdout_fn,
        stderr_fn=stderr_fn,
    )

    stderr_message = stderr_fn.call_args.args[0]
    assert "deprecated" in stderr_message
    assert "`jukebox-admin --library '/tmp/custom library.json' settings show --effective --json`" in stderr_message
    stdout_fn.assert_called_once()


def test_execute_sonos_command_lists_visible_sonos_speakers():
    stdout_fn = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        ),
        DiscoveredSonosSpeaker(
            uid="speaker-2",
            name="Living Room",
            host="192.168.1.40",
            household_id="household-1",
            is_visible=True,
        ),
    ]

    execute_sonos_command(
        command=SonosListCommand(type="sonos_list"),
        sonos_service=sonos_service,
        stdout_fn=stdout_fn,
    )

    sonos_service.list_available_speakers.assert_called_once_with()
    rendered_output = stdout_fn.call_args.args[0]
    assert "1. Kitchen" in rendered_output
    assert "speaker-1" in rendered_output


def test_execute_sonos_command_preserves_sonos_discovery_failures():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.side_effect = SonosDiscoveryError(
        "Failed to discover Sonos speakers: network unavailable"
    )

    with pytest.raises(SonosDiscoveryError, match="network unavailable"):
        execute_sonos_command(
            command=SonosListCommand(type="sonos_list"),
            sonos_service=sonos_service,
        )


def test_execute_sonos_command_selects_requested_uid_and_renders_success():
    stdout_fn = MagicMock()
    sonos_service = MagicMock()
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "message": "Settings saved. Changes take effect after restart."
    }
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]

    execute_sonos_command(
        command=SonosSelectCommand(type="sonos_select", uids=["speaker-1"]),
        sonos_service=sonos_service,
        settings_service=settings_service,
        stdout_fn=stdout_fn,
    )

    settings_service.patch_persisted_settings.assert_called_once()
    rendered_output = stdout_fn.call_args.args[0]
    assert "Selected Sonos speaker: Kitchen" in rendered_output
    assert "UID: speaker-1" in rendered_output


def test_execute_sonos_command_selects_single_discovered_speaker_without_prompt():
    stdout_fn = MagicMock()
    prompt_fn = MagicMock()
    sonos_service = MagicMock()
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]

    execute_sonos_command(
        command=SonosSelectCommand(type="sonos_select"),
        sonos_service=sonos_service,
        settings_service=settings_service,
        speaker_prompt_fn=prompt_fn,
        stdout_fn=stdout_fn,
    )

    prompt_fn.assert_not_called()
    settings_service.patch_persisted_settings.assert_called_once()


def test_execute_sonos_command_uses_prompt_for_multiple_speakers():
    stdout_fn = MagicMock()
    prompt_fn = MagicMock(return_value="speaker-2")
    sonos_service = MagicMock()
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        ),
        DiscoveredSonosSpeaker(
            uid="speaker-2",
            name="Kitchen",
            host="192.168.1.31",
            household_id="household-1",
            is_visible=True,
        ),
    ]

    execute_sonos_command(
        command=SonosSelectCommand(type="sonos_select"),
        sonos_service=sonos_service,
        settings_service=settings_service,
        speaker_prompt_fn=prompt_fn,
        stdout_fn=stdout_fn,
    )

    prompt_fn.assert_called_once_with(sonos_service.list_available_speakers.return_value)
    settings_service.patch_persisted_settings.assert_called_once()
    assert "speaker-2" in stdout_fn.call_args.args[0]


def test_execute_sonos_command_cancel_does_not_write_settings():
    stdout_fn = MagicMock()
    prompt_fn = MagicMock(return_value=None)
    sonos_service = MagicMock()
    settings_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        ),
        DiscoveredSonosSpeaker(
            uid="speaker-2",
            name="Living Room",
            host="192.168.1.31",
            household_id="household-1",
            is_visible=True,
        ),
    ]

    execute_sonos_command(
        command=SonosSelectCommand(type="sonos_select"),
        sonos_service=sonos_service,
        settings_service=settings_service,
        speaker_prompt_fn=prompt_fn,
        stdout_fn=stdout_fn,
    )

    settings_service.patch_persisted_settings.assert_not_called()
    stdout_fn.assert_not_called()


def test_execute_sonos_command_show_renders_saved_selection_status():
    stdout_fn = MagicMock()
    sonos_service = MagicMock()
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
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
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]

    execute_sonos_command(
        command=SonosShowCommand(type="sonos_show"),
        sonos_service=sonos_service,
        settings_service=settings_service,
        stdout_fn=stdout_fn,
    )

    rendered_output = stdout_fn.call_args.args[0]
    assert "Selected Sonos Speaker" in rendered_output
    assert "- Status: available" in rendered_output
    assert "- Host: 192.168.1.30" in rendered_output


def test_execute_sonos_command_rejects_multiple_scripted_uids():
    sonos_service = MagicMock()
    settings_service = MagicMock()
    sonos_service.list_available_speakers.return_value = []

    with pytest.raises(RuntimeError, match="requires exactly one UID"):
        execute_sonos_command(
            command=SonosSelectCommand(type="sonos_select", uids=["speaker-1", "speaker-2"]),
            sonos_service=sonos_service,
            settings_service=settings_service,
        )


@pytest.mark.parametrize(
    ("command", "builder_name", "expected_port"),
    [
        (ApiCommand(type="api", port=1111), "build_api_app", 7777),
        (UiCommand(type="ui", port=2222), "build_ui_app", 8888),
    ],
)
def test_execute_server_command_starts_server_with_resolved_runtime(mocker, command, builder_name, expected_port):
    mock_uvicorn = mocker.patch.dict("sys.modules", {"uvicorn": MagicMock()})["uvicorn"]
    services = build_services()
    services.settings.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=7777,
        ui_port=8888,
        verbose=True,
    )
    fake_app = MagicMock(app=MagicMock(name="server_app"))
    build_api_app = MagicMock(return_value=fake_app)
    build_ui_app = MagicMock(return_value=fake_app)

    execute_server_command(
        verbose=True,
        command=command,
        services=services,
        build_api_app=build_api_app,
        build_ui_app=build_ui_app,
        source_command="jukebox-admin",
    )

    services.settings.resolve_admin_runtime.assert_called_once_with(verbose=True)
    if builder_name == "build_api_app":
        build_api_app.assert_called_once_with("/resolved/library.json", services)
        build_ui_app.assert_not_called()
    else:
        build_ui_app.assert_called_once_with("/resolved/library.json", services)
        build_api_app.assert_not_called()
    mock_uvicorn.run.assert_called_once_with(fake_app.app, host="0.0.0.0", port=expected_port)


@pytest.mark.parametrize(
    ("command", "extra_name"),
    [
        (ApiCommand(type="api", port=1234), "api"),
        (UiCommand(type="ui", port=1234), "ui"),
    ],
)
def test_execute_server_command_reports_missing_optional_dependencies(mocker, command, extra_name):
    services = build_services()
    services.settings.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
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
        execute_server_command(
            verbose=False,
            command=command,
            services=services,
            build_api_app=MagicMock(),
            build_ui_app=MagicMock(),
            source_command="jukebox-admin",
        )

    assert f"`jukebox-admin {extra_name}` requires the optional `{extra_name}` dependencies." in str(err.value)


@pytest.mark.parametrize(
    ("command", "extra_name", "builder_name"),
    [
        (ApiCommand(type="api", port=1234), "api", "build_api_app"),
        (UiCommand(type="ui", port=1234), "ui", "build_ui_app"),
    ],
)
def test_execute_server_command_rewrites_controller_dependency_failures(mocker, command, extra_name, builder_name):
    services = build_services()
    services.settings.resolve_admin_runtime.return_value = ResolvedAdminRuntimeConfig(
        library_path="/resolved/library.json",
        api_port=8000,
        ui_port=9000,
        verbose=False,
    )
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
        execute_server_command(
            verbose=False,
            command=command,
            services=services,
            build_api_app=build_api_app,
            build_ui_app=build_ui_app,
            source_command="jukebox-admin",
        )

    assert str(err.value) == optional_extra_dependency_message(
        subject=f"`jukebox-admin {extra_name}`",
        extra_name=extra_name,
        source_command=f"jukebox-admin {extra_name}",
    )
