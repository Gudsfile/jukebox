import json
from importlib import util
from unittest.mock import MagicMock

import pytest

FASTUI_INSTALLED = util.find_spec("fastui") is not None


def build_settings_page_builder():
    from jukebox.adapters.inbound.admin.ui_pages.settings import SettingsUIPageBuilder

    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}, "ui": {"port": 8000}},
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "household_id": "household-1",
                        "coordinator_uid": "speaker-2",
                        "members": [
                            {"uid": "speaker-1"},
                            {"uid": "speaker-2"},
                        ],
                    }
                }
            }
        },
    }
    settings_service.get_effective_settings_view.return_value = {
        "settings": {
            "paths": {"library_path": "~/.jukebox/library.json"},
            "admin": {"api": {"port": 8100}, "ui": {"port": 8000}},
            "jukebox": {
                "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                "runtime": {"loop_interval_seconds": 0.1},
                "reader": {"type": "dryrun", "pn532": {"read_timeout_seconds": 0.1}},
                "player": {
                    "type": "dryrun",
                    "sonos": {
                        "selected_group": {
                            "household_id": "household-1",
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
                "reader": {"type": "default", "pn532": {"read_timeout_seconds": "default"}},
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
        "derived": {},
        "change_metadata": {},
    }

    return SettingsUIPageBuilder(settings_service=settings_service)


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_settings_page_groups_entries_and_shows_persisted_and_effective_values(walk_components):
    page_builder = build_settings_page_builder()

    page = page_builder.build_settings_page_components(toast="toast-settings-success", toast_message="Settings saved.")
    all_components = list(walk_components(page[0].components))

    assert any(component.type == "Heading" and component.text == "Settings" for component in all_components)
    back_link = next(
        component
        for component in all_components
        if component.type == "Link" and getattr(component.on_click, "url", None) == "/"
    )
    assert back_link.components[0].text == "Back to Library"
    assert any(
        component.type == "Paragraph" and component.text == "Ports used by the admin API and admin UI processes."
        for component in all_components
    )
    settings_headings = [
        component.text for component in all_components if component.type == "Heading" and component.level == 2
    ]
    assert settings_headings == ["Paths", "Admin", "Playback", "Player", "Reader"]
    assert any(component.type == "Heading" and component.text == "Admin" for component in all_components)
    assert any(component.type == "Heading" and component.text == "Player" for component in all_components)
    assert any(component.type == "Button" and component.text == "Edit ✏️" for component in all_components)
    manage_speakers_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "Manage Speakers 🔊"
    )
    assert any(component.type == "Paragraph" and component.text == "Persisted override" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "8100" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "8000" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "None" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Settings file" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Configured" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Pinned default" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Restart required" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Dry Run" for component in all_components)
    assert any(
        component.type == "Paragraph" and component.text == "speaker-2 (coordinator); members: speaker-1, speaker-2"
        for component in all_components
    )
    assert manage_speakers_button.on_click.url == "/sonos"
    assert "text-nowrap" in manage_speakers_button.class_name
    assert not any(component.type == "Button" and component.text == "Reset" for component in all_components)
    assert page[1].event.name == "toast-settings-success"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_settings_edit_pages_render_select_text_and_json_fields(walk_components):
    page_builder = build_settings_page_builder()

    select_page = page_builder.build_settings_edit_page_components("jukebox.reader.type")[0]
    select_form = next(component for component in walk_components(select_page.components) if component.type == "Form")
    select_field = select_form.form_fields[0]
    assert select_field.type == "FormFieldSelect"
    assert select_field.initial == "dryrun"
    assert select_field.options == [
        {"value": "dryrun", "label": "Dry Run"},
        {"value": "pn532", "label": "Pn532 NFC"},
    ]

    text_page = page_builder.build_settings_edit_page_components("admin.ui.port")[0]
    assert any(
        component.type == "Heading" and component.text == "Current values"
        for component in walk_components(text_page.components)
    )
    assert any(
        component.type == "Paragraph" and component.text == "Pinned default"
        for component in walk_components(text_page.components)
    )
    text_form = next(component for component in walk_components(text_page.components) if component.type == "Form")
    text_field = text_form.form_fields[0]
    assert text_field.type == "FormFieldInput"
    assert text_field.initial == "8000"
    assert text_field.html_type == "number"

    number_page = page_builder.build_settings_edit_page_components("jukebox.playback.pause_delay_seconds")[0]
    number_form = next(component for component in walk_components(number_page.components) if component.type == "Form")
    number_field = number_form.form_fields[0]
    assert number_field.type == "FormFieldInput"
    assert number_field.initial == "0.25"
    assert number_field.html_type == "text"

    object_page = page_builder.build_settings_edit_page_components("jukebox.player.sonos.selected_group")[0]
    object_form = next(component for component in walk_components(object_page.components) if component.type == "Form")
    object_field = object_form.form_fields[0]
    assert object_field.type == "FormFieldTextarea"
    assert object_field.initial == json.dumps(
        {
            "household_id": "household-1",
            "coordinator_uid": "speaker-2",
            "members": [
                {"uid": "speaker-1"},
                {"uid": "speaker-2"},
            ],
        },
        indent=2,
    )
    reset_form = next(
        component
        for component in walk_components(text_page.components)
        if component.type == "Form" and component.submit_url == "/api/ui/settings/admin.ui.port/reset"
    )
    assert reset_form.method == "POST"
    assert reset_form.footer[0].type == "Button"
    assert reset_form.footer[0].text == "Reset"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_settings_pages_render_error_banner_when_effective_settings_are_unavailable(walk_components):
    from jukebox.settings.errors import InvalidSettingsError

    page_builder = build_settings_page_builder()
    page_builder.settings_service.get_effective_settings_view.side_effect = InvalidSettingsError(
        "Invalid effective settings after environment overrides."
    )

    settings_page = page_builder.build_settings_page_components()[0]
    settings_components = list(walk_components(settings_page.components))

    assert any(
        component.type == "Error"
        and component.title == "Effective settings unavailable"
        and "Invalid effective settings after environment overrides." in component.description
        for component in settings_components
    )
    assert any(component.type == "Paragraph" and component.text == "8100" for component in settings_components)
    assert any(component.type == "Paragraph" and component.text == "unknown" for component in settings_components)

    edit_page = page_builder.build_settings_edit_page_components("admin.api.port")[0]
    edit_components = list(walk_components(edit_page.components))

    assert any(
        component.type == "Error"
        and component.title == "Effective settings unavailable"
        and "Showing persisted and default values where possible" in component.description
        for component in edit_components
    )
    assert any(component.type == "Paragraph" and component.text == "8000" for component in edit_components)
    assert any(component.type == "Paragraph" and component.text == "8100" for component in edit_components)


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_settings_page_renders_mixed_provenance_label(walk_components):
    page_builder = build_settings_page_builder()
    page_builder.settings_service.get_effective_settings_view.return_value["provenance"]["jukebox"]["player"]["sonos"][
        "selected_group"
    ] = {
        "coordinator_uid": "file",
        "members": "env",
    }

    page = page_builder.build_settings_page_components()[0]
    all_components = list(walk_components(page.components))

    assert any(component.type == "Paragraph" and component.text == "Mixed source" for component in all_components)


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_settings_edit_page_renders_empty_object_field_with_placeholder_when_no_value(walk_components):
    page_builder = build_settings_page_builder()
    page_builder.settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    page_builder.settings_service.get_effective_settings_view.return_value = {
        "settings": {
            "paths": {"library_path": "~/.jukebox/library.json"},
            "admin": {"api": {"port": 8000}, "ui": {"port": 8000}},
            "jukebox": {
                "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                "runtime": {"loop_interval_seconds": 0.1},
                "reader": {"type": "dryrun", "pn532": {"read_timeout_seconds": 0.1}},
                "player": {
                    "type": "dryrun",
                    "sonos": {
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
                "reader": {"type": "default", "pn532": {"read_timeout_seconds": "default"}},
                "player": {
                    "type": "default",
                    "sonos": {
                        "selected_group": "default",
                    },
                },
            },
        },
        "derived": {},
        "change_metadata": {},
    }

    object_page = page_builder.build_settings_edit_page_components("jukebox.player.sonos.selected_group")[0]
    object_form = next(component for component in walk_components(object_page.components) if component.type == "Form")
    object_field = object_form.form_fields[0]

    assert object_field.type == "FormFieldTextarea"
    assert object_field.initial == ""
    assert object_field.placeholder == "Enter a JSON object. Leave blank to persist null."
    assert object_field.description.endswith(
        "Enter a JSON object matching the persisted setting shape. Leave blank to persist null. Use Reset to remove the persisted override. Takes effect after restart."
    )
