from typing import cast

from jukebox.settings.definitions import build_change_metadata_tree, build_editable_setting_displays
from jukebox.settings.types import JsonObject


def test_build_change_metadata_tree_includes_field_choices():
    metadata = build_change_metadata_tree()
    jukebox_metadata = cast(JsonObject, metadata["jukebox"])
    reader_metadata = cast(JsonObject, jukebox_metadata["reader"])
    player_metadata = cast(JsonObject, jukebox_metadata["player"])
    reader_type_metadata = cast(JsonObject, reader_metadata["type"])
    player_type_metadata = cast(JsonObject, player_metadata["type"])

    assert reader_type_metadata["choices"] == [
        {"value": "dryrun", "label": "Dry Run"},
        {"value": "nfc", "label": "NFC"},
    ]
    assert player_type_metadata["choices"] == [
        {"value": "dryrun", "label": "Dry Run"},
        {"value": "sonos", "label": "Sonos"},
    ]


def test_build_editable_setting_displays_flattens_values_and_collapses_object_provenance():
    displays = build_editable_setting_displays(
        {
            "schema_version": 1,
            "admin": {"api": {"port": 8100}, "ui": {"port": 8000}},
            "jukebox": {
                "player": {
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-2",
                            "members": [
                                {"uid": "speaker-1"},
                                {"uid": "speaker-2"},
                            ],
                        }
                    }
                }
            },
        },
        {
            "settings": {
                "paths": {"library_path": "~/.jukebox/library.json"},
                "admin": {"api": {"port": 8100}, "ui": {"port": 8000}},
                "jukebox": {
                    "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                    "runtime": {"loop_interval_seconds": 0.1},
                    "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
                    "player": {
                        "type": "dryrun",
                        "sonos": {
                            "selected_group": {
                                "coordinator_uid": "speaker-2",
                                "members": [
                                    {"uid": "speaker-1"},
                                    {"uid": "speaker-2"},
                                ],
                            }
                        },
                    },
                },
            },
            "provenance": {
                "paths": {"library_path": "default"},
                "admin": {"api": {"port": "file"}, "ui": {"port": "file"}},
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
                            }
                        },
                    },
                },
            },
        },
    )

    admin_api_port = next(display for display in displays if display.path == "admin.api.port")
    assert admin_api_port.persisted_value == 8100
    assert admin_api_port.effective_value == 8100
    assert admin_api_port.provenance == "file"
    assert admin_api_port.is_persisted is True

    admin_ui_port = next(display for display in displays if display.path == "admin.ui.port")
    assert admin_ui_port.default_value == 8000
    assert admin_ui_port.persisted_value == 8000
    assert admin_ui_port.effective_value == 8000
    assert admin_ui_port.provenance == "file"
    assert admin_ui_port.is_persisted is True
    assert admin_ui_port.is_pinned_default is True

    selected_group = next(display for display in displays if display.path == "jukebox.player.sonos.selected_group")
    assert selected_group.provenance == "file"
    assert selected_group.is_persisted is True
    assert selected_group.persisted_value == {
        "coordinator_uid": "speaker-2",
        "members": [
            {"uid": "speaker-1"},
            {"uid": "speaker-2"},
        ],
    }
