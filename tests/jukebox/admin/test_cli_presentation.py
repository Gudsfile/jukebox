from jukebox.admin.cli_presentation import (
    build_discstore_settings_deprecation_warning,
    render_cli_error,
    render_settings_output,
)
from jukebox.admin.commands import SettingsResetCommand, SettingsSetCommand, SettingsShowCommand
from jukebox.settings.errors import (
    InvalidSettingsError,
    MalformedSettingsFileError,
    UnsupportedSettingsVersionError,
)


def test_render_settings_output_persisted_groups_overrides_by_section():
    rendered = render_settings_output(
        SettingsShowCommand(type="settings_show"),
        {
            "schema_version": 1,
            "paths": {"library_path": "~/music/library.json"},
            "admin": {"api": {"port": 8100}},
            "jukebox": {
                "player": {
                    "sonos": {
                        "manual_host": "192.168.1.20",
                        "selected_group": {
                            "coordinator_uid": "speaker-2",
                            "members": [
                                {"uid": "speaker-1", "name": "Kitchen"},
                                {"uid": "speaker-2", "name": "Living Room"},
                            ],
                        },
                    }
                }
            },
        },
    )

    assert "Persisted Settings" in rendered
    assert "Schema Version: 1" in rendered
    assert "Paths" in rendered
    assert "Library Path [paths.library_path]: ~/music/library.json" in rendered
    assert "Admin" in rendered
    assert "Admin API Port [admin.api.port]: 8100" in rendered
    assert "Player" in rendered
    assert "jukebox.player.sonos.manual_host: 192.168.1.20" in rendered
    assert (
        "Selected Sonos Group [jukebox.player.sonos.selected_group]: "
        "Living Room (coordinator); members: Kitchen, Living Room"
    ) in rendered


def test_render_settings_output_reset_noop_is_concise():
    rendered = render_settings_output(
        SettingsResetCommand(type="settings_reset", dotted_path="admin"),
        {
            "updated_paths": [],
            "restart_required": False,
            "restart_required_paths": [],
            "message": "No persisted settings changed.",
        },
    )

    assert rendered == "No persisted settings changed.\n\nRestart Required: no"


def test_render_settings_output_json_mode_preserves_payload_shape():
    command = SettingsSetCommand(
        type="settings_set",
        dotted_path="admin.api.port",
        value="9000",
        json_output=True,
    )
    payload = {"persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}}

    assert (
        render_settings_output(command, payload)
        == '{\n  "persisted": {\n    "schema_version": 1,\n    "admin": {\n      "api": {\n        "port": 9000\n      }\n    }\n  }\n}'
    )


def test_build_discstore_settings_deprecation_warning_points_to_equivalent_command():
    warning = build_discstore_settings_deprecation_warning(
        SettingsShowCommand(type="settings_show", effective=True, json_output=True)
    )

    assert "deprecated" in warning
    assert "`jukebox-admin settings show --effective --json`" in warning


def test_render_cli_error_for_unsupported_settings_path_is_actionable():
    message = render_cli_error(InvalidSettingsError("Unsupported settings path for write: 'admin.api.host'"))

    assert "Unsupported settings path: 'admin.api.host'." in message
    assert "`jukebox-admin settings show --effective --json`" in message


def test_render_cli_error_for_invalid_json_value_is_concise():
    message = render_cli_error(
        InvalidSettingsError("Settings value for 'jukebox.player.sonos.selected_group' must be valid JSON.")
    )

    assert message == "Invalid value for 'jukebox.player.sonos.selected_group'. Pass a JSON object or `null`."


def test_render_cli_error_for_malformed_settings_file_is_friendly():
    message = render_cli_error(
        MalformedSettingsFileError("Malformed settings file at '/tmp/settings.json': Expecting value: line 1 column 1")
    )

    assert message == "Malformed settings file at '/tmp/settings.json'. Fix the JSON syntax and try again."


def test_render_cli_error_for_unsupported_schema_version_is_friendly():
    message = render_cli_error(
        UnsupportedSettingsVersionError("Unsupported settings schema_version 3; this build supports version 1.")
    )

    assert message == (
        "Unsupported settings file version. Unsupported settings schema_version 3; this build supports version 1."
    )


def test_render_cli_error_for_optional_dependency_exit_is_concise():
    message = render_cli_error(
        SystemExit(
            "The `ui_controller` module requires the optional `ui` dependencies.\n\n"
            "If you're running from a source checkout:\n"
            "  uv sync --extra ui\n"
            "or \n"
            "  uv run --extra ui jukebox-admin ui"
        )
    )

    assert "Optional `ui` dependencies are not installed." in message
    assert "`uv sync --extra ui`" in message
    assert "`uv run --extra ui jukebox-admin ui`" in message
