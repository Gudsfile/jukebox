from jukebox.admin.cli_presentation import (
    build_discstore_settings_deprecation_warning,
    build_sonos_speaker_choice_label,
    render_cli_error,
    render_settings_output,
    render_sonos_selection_saved_output,
    render_sonos_selection_status_output,
    render_sonos_speakers_output,
)
from jukebox.admin.commands import SettingsResetCommand, SettingsSetCommand, SettingsShowCommand
from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.settings.errors import (
    InvalidSettingsError,
    MalformedSettingsFileError,
    UnsupportedSettingsVersionError,
)
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import SonosSelectionAvailability, SonosSelectionResult, SonosSelectionStatus


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
                        "selected_group": {
                            "coordinator_uid": "speaker-2",
                            "members": [
                                {"uid": "speaker-1"},
                                {"uid": "speaker-2"},
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
    assert (
        "Selected Sonos Group [jukebox.player.sonos.selected_group]: "
        "speaker-2 (coordinator); members: speaker-1, speaker-2"
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


def test_render_settings_output_effective_includes_manual_sonos_targets():
    rendered = render_settings_output(
        SettingsShowCommand(type="settings_show", effective=True),
        {
            "settings": {
                "paths": {"library_path": "~/.config/jukebox/library.json"},
                "admin": {"api": {"port": 8000}, "ui": {"port": 8000}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                    "runtime": {"loop_interval_seconds": 0.1},
                    "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "manual_host": "192.168.1.20",
                            "manual_name": "Living Room",
                            "selected_group": None,
                        },
                    },
                },
            },
            "provenance": {
                "paths": {"library_path": "default"},
                "admin": {"api": {"port": "default"}, "ui": {"port": "default"}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                    "runtime": {"loop_interval_seconds": "default"},
                    "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                    "player": {
                        "type": "file",
                        "sonos": {
                            "manual_host": "env",
                            "manual_name": "cli",
                            "selected_group": "default",
                        },
                    },
                },
            },
            "derived": {},
            "settings_metadata": {},
        },
    )

    assert "jukebox.player.sonos.manual_host: 192.168.1.20 (source: env)" in rendered
    assert "jukebox.player.sonos.manual_name: Living Room (source: cli)" in rendered


def test_render_settings_output_effective_treats_selected_group_as_atomic():
    rendered = render_settings_output(
        SettingsShowCommand(type="settings_show", effective=True),
        {
            "settings": {
                "paths": {"library_path": "~/.config/jukebox/library.json"},
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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
                    },
                },
            },
            "provenance": {
                "paths": {"library_path": "default"},
                "admin": {"api": {"port": "default"}, "ui": {"port": "default"}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                    "runtime": {"loop_interval_seconds": "default"},
                    "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                    "player": {
                        "type": "file",
                        "sonos": {
                            "selected_group": "file",
                        },
                    },
                },
            },
            "derived": {},
            "settings_metadata": {},
        },
    )

    assert (
        "Selected Sonos Group [jukebox.player.sonos.selected_group]: "
        "speaker-2 (coordinator); members: speaker-1, speaker-2 (source: file; restart required)"
    ) in rendered
    assert "jukebox.player.sonos.selected_group.coordinator_uid" not in rendered
    assert "jukebox.player.sonos.selected_group.members" not in rendered


def test_render_settings_output_effective_collapses_nested_selected_group_provenance():
    rendered = render_settings_output(
        SettingsShowCommand(type="settings_show", effective=True),
        {
            "settings": {
                "paths": {"library_path": "~/.config/jukebox/library.json"},
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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
                    },
                },
            },
            "provenance": {
                "paths": {"library_path": "default"},
                "admin": {"api": {"port": "default"}, "ui": {"port": "default"}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                    "runtime": {"loop_interval_seconds": "default"},
                    "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                    "player": {
                        "type": "default",
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "file",
                                "members": "file",
                            },
                        },
                    },
                },
            },
            "derived": {},
            "settings_metadata": {},
        },
    )

    assert (
        "Selected Sonos Group [jukebox.player.sonos.selected_group]: "
        "speaker-2 (coordinator); members: speaker-1, speaker-2 (source: file; restart required)"
    ) in rendered


def test_render_settings_output_effective_reports_mixed_nested_provenance():
    rendered = render_settings_output(
        SettingsShowCommand(type="settings_show", effective=True),
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
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            },
                        },
                    },
                },
            },
            "provenance": {
                "paths": {"library_path": "default"},
                "admin": {"api": {"port": "default"}, "ui": {"port": "default"}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": "default", "pause_delay_seconds": "default"},
                    "runtime": {"loop_interval_seconds": "default"},
                    "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
                    "player": {
                        "type": "default",
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "file",
                                "members": "env",
                            },
                        },
                    },
                },
            },
            "derived": {},
            "settings_metadata": {},
        },
    )

    assert (
        "Selected Sonos Group [jukebox.player.sonos.selected_group]: "
        "speaker-2 (coordinator); members: speaker-1, speaker-2 (source: mixed; restart required)"
    ) in rendered


def test_render_sonos_speakers_output_is_stable_and_human_readable():
    rendered = render_sonos_speakers_output(
        [
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
                host="192.168.1.40",
                household_id="household-1",
                is_visible=True,
            ),
        ]
    )

    assert "1. Kitchen   192.168.1.30   speaker-1" in rendered
    assert "2. Kitchen   192.168.1.40   speaker-2" in rendered


def test_render_sonos_speakers_output_handles_empty_results():
    assert render_sonos_speakers_output([]) == "No visible Sonos speakers found."


def test_build_sonos_speaker_choice_label_includes_host_for_disambiguation():
    assert (
        build_sonos_speaker_choice_label(
            DiscoveredSonosSpeaker(
                uid="speaker-1",
                name="Kitchen",
                host="192.168.1.30",
                household_id="household-1",
                is_visible=True,
            )
        )
        == "Kitchen (192.168.1.30)"
    )


def test_render_sonos_selection_saved_output_is_human_readable():
    rendered = render_sonos_selection_saved_output(
        SonosSelectionResult(
            speaker=DiscoveredSonosSpeaker(
                uid="speaker-1",
                name="Kitchen",
                host="192.168.1.30",
                household_id="household-1",
                is_visible=True,
            ),
            selected_group=SelectedSonosGroupSettings(
                coordinator_uid="speaker-1",
                members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
            ),
            settings_message="Settings saved. Changes take effect after restart.",
        )
    )

    assert "Selected Sonos speaker: Kitchen" in rendered
    assert "UID: speaker-1" in rendered
    assert "Settings saved. Changes take effect after restart." in rendered


def test_render_sonos_selection_status_output_for_not_selected():
    rendered = render_sonos_selection_status_output(
        SonosSelectionStatus(
            selected_group=None,
            availability=SonosSelectionAvailability(status="not_selected", speaker=None),
        )
    )

    assert rendered == "Selected Sonos Speaker\n\n- Status: not selected"


def test_render_sonos_selection_status_output_for_available_selection():
    rendered = render_sonos_selection_status_output(
        SonosSelectionStatus(
            selected_group=SelectedSonosGroupSettings(
                coordinator_uid="speaker-1",
                members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
            ),
            availability=SonosSelectionAvailability(
                status="available",
                speaker=DiscoveredSonosSpeaker(
                    uid="speaker-1",
                    name="Kitchen",
                    host="192.168.1.30",
                    household_id="household-1",
                    is_visible=True,
                ),
            ),
        )
    )

    assert "Selected Sonos Speaker" in rendered
    assert "- UID: speaker-1" in rendered
    assert "- Status: available" in rendered
    assert "- Household: household-1" in rendered


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


def test_build_discstore_settings_deprecation_warning_shell_quotes_settings_values():
    warning = build_discstore_settings_deprecation_warning(
        SettingsSetCommand(
            type="settings_set",
            dotted_path="jukebox.player.sonos.selected_group",
            value='{"coordinator_uid": "speaker-1"}',
        )
    )

    assert (
        '`jukebox-admin settings set jukebox.player.sonos.selected_group \'{"coordinator_uid": "speaker-1"}\'`'
    ) in warning


def test_build_discstore_settings_deprecation_warning_preserves_library_override():
    warning = build_discstore_settings_deprecation_warning(
        SettingsShowCommand(type="settings_show", effective=True),
        library="/tmp/custom library.json",
    )

    assert "`jukebox-admin --library '/tmp/custom library.json' settings show --effective`" in warning


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


def test_render_cli_error_for_invalid_settings_file_preserves_failing_path():
    message = render_cli_error(
        InvalidSettingsError(
            "Invalid settings file at '/tmp/settings.json': 1 validation error for SparseAppSettings\n"
            "admin.api.port\n"
            "  Input should be a valid integer, unable to parse string as an integer "
            "[type=int_parsing, input_value='bad', input_type=str]\n"
            "For further information visit https://errors.pydantic.dev/2.11/v/int_parsing"
        )
    )

    assert message == (
        "Persisted settings are invalid at '/tmp/settings.json': "
        "admin.api.port: Input should be a valid integer, unable to parse string as an integer"
    )


def test_render_cli_error_for_invalid_effective_settings_preserves_failing_paths():
    message = render_cli_error(
        InvalidSettingsError(
            "Invalid effective settings after environment overrides: 2 validation errors for AppSettings\n"
            "admin.api.port\n"
            "  Input should be a valid integer, unable to parse string as an integer "
            "[type=int_parsing, input_value='bad', input_type=str]\n"
            "admin.ui.port\n"
            "  Input should be less than or equal to 65535 [type=less_than_equal, input_value=70000, input_type=int]\n"
            "For further information visit https://errors.pydantic.dev/2.11/v/int_parsing"
        )
    )

    assert message == (
        "Effective settings are invalid: "
        "admin.api.port: Input should be a valid integer, unable to parse string as an integer; "
        "admin.ui.port: Input should be less than or equal to 65535"
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
