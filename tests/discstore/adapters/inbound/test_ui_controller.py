import json
import sys
from importlib import util
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_module_import_failure():
    version_below_py37 = (3, 7, 17, "final", 0)
    with mock.patch("sys.version_info", version_below_py37), pytest.raises(RuntimeError) as err:
        import discstore.adapters.inbound.ui_controller  # noqa: F401

    assert "The `ui_controller` module requires Python 3.10+." in str(err.value)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="FastUI requires Python 3.10+")
def test_dependencies_import_failure(mocker):
    sys.modules.pop("discstore.adapters.inbound.ui_controller", None)
    mocker.patch.dict("sys.modules", {"fastui": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.ui_controller  # noqa: F401

    assert "The `ui_controller` module requires the optional `ui` dependencies." in str(err.value)
    assert "pip install 'gukebox[ui]'" in str(err.value)
    assert "uv sync --extra ui" in str(err.value)
    assert "uv run --extra ui discstore ui" in str(err.value)


def build_controller():
    from discstore.adapters.inbound.ui_controller import UIController

    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "admin": {"api": {"port": 8100}, "ui": {"port": 8000}},
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-2",
                        "members": [
                            {"uid": "speaker-1", "name": "Kitchen"},
                            {"uid": "speaker-2", "name": "Living Room"},
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
                "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
                "player": {
                    "type": "dryrun",
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
        "derived": {},
        "change_metadata": {},
    }

    return UIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_disc=MagicMock(),
        get_current_tag_status=MagicMock(),
        settings_service=settings_service,
    )


def walk_components(components):
    for component in components:
        yield component
        children = getattr(component, "components", None)
        if children:
            yield from walk_components(children)


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_ui_controller_registers_fastui_routes_and_page_structure():
    from discstore.domain.entities import Disc, DiscMetadata, DiscOption

    controller = build_controller()
    controller.list_discs.execute.return_value = {
        "tag-123": Disc(
            uri="/music/song.mp3",
            metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
            option=DiscOption(shuffle=True),
        )
    }
    controller.get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    controller.remove_disc.execute.return_value = None

    route_index = {
        (getattr(route, "path", None), tuple(sorted(getattr(route, "methods", []))))
        for route in controller.app.routes
        if hasattr(route, "path")
    }

    assert ("/{path:path}", ("GET",)) in route_index
    assert ("/api/ui/", ("GET",)) in route_index
    assert ("/api/ui/current-tag-banner/events", ("GET",)) in route_index
    assert ("/api/ui/discs/new", ("GET",)) in route_index
    assert ("/api/ui/discs", ("POST",)) in route_index
    assert ("/api/ui/discs/{tag_id}/edit", ("GET",)) in route_index
    assert ("/api/ui/discs/{tag_id}", ("POST",)) in route_index
    assert ("/api/ui/discs/{tag_id}/delete", ("GET",)) in route_index
    assert ("/api/ui/discs/{tag_id}/delete", ("POST",)) in route_index
    assert ("/api/ui/settings", ("GET",)) in route_index
    assert ("/api/ui/settings/{setting_path}/edit", ("GET",)) in route_index
    assert ("/api/ui/settings/{setting_path}", ("POST",)) in route_index
    assert ("/api/ui/settings/{setting_path}/reset", ("POST",)) in route_index
    assert ("/api/v1/discs", ("GET",)) in route_index
    assert ("/api/v1/current-tag", ("GET",)) in route_index
    assert ("/api/v1/disc", ("POST",)) in route_index
    assert ("/api/v1/disc", ("DELETE",)) in route_index

    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/")
    page = route.endpoint()[0]
    all_components = list(walk_components(page.components))
    server_load = next(component for component in all_components if component.type == "ServerLoad")
    add_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "➕ Add a new disc"
    )
    settings_button = next(
        component for component in all_components if component.type == "Button" and component.text == "⚙️ Settings"
    )
    edit_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "Edit ✏️" and component.on_click is not None
    )
    assert any(component.type == "Paragraph" and component.text == "URI / Path" for component in all_components)

    assert server_load.path == "/current-tag-banner/events"
    assert server_load.sse is True
    assert add_button.on_click.type == "go-to"
    assert add_button.on_click.url == "/discs/new"
    assert settings_button.on_click.type == "go-to"
    assert settings_button.on_click.url == "/settings"
    assert edit_button.on_click.type == "go-to"
    assert edit_button.on_click.url == "/discs/tag-123/edit"

    new_route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/discs/new")
    new_page = new_route.endpoint()[0]
    assert new_page.components[0].text == "Add disc"

    edit_route = next(
        route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/discs/{tag_id}/edit"
    )
    edit_page = edit_route.endpoint("tag-123")[0]
    assert edit_page.components[0].text == "Edit disc tag-123"
    delete_button = next(
        component
        for component in edit_page.components
        if component.type == "Button" and component.text == "🗑️ Delete this disc"
    )
    assert delete_button.on_click.type == "go-to"
    assert delete_button.on_click.url == "/discs/tag-123/delete"

    delete_route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}/delete" and "GET" in getattr(route, "methods", [])
    )
    delete_page = delete_route.endpoint("tag-123")[0]
    assert delete_page.components[0].text == "Delete disc tag-123"
    assert delete_page.components[1].text == 'Are you sure you want to delete the disc with tag "tag-123"?'
    all_delete_page_components = list(walk_components(delete_page.components))
    confirm_deletion_form = next(component for component in all_delete_page_components if component.type == "Form")
    cancel_deletion_button = next(
        component
        for component in all_delete_page_components
        if component.type == "Button" and component.text == "Cancel"
    )
    assert confirm_deletion_form.submit_url == "/api/ui/discs/tag-123/delete"
    assert cancel_deletion_button.on_click.type == "back"

    html_route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/{path:path}")
    html_response = html_route.endpoint("discs/new")
    assert html_response.status_code == 200
    assert "/api/ui" in html_response.body.decode("utf-8")


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_settings_page_groups_entries_and_shows_persisted_and_effective_values():
    controller = build_controller()

    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/settings")
    page = route.endpoint(toast="toast-settings-success", toast_message="Settings saved.")
    all_components = list(walk_components(page[0].components))

    assert any(component.type == "Heading" and component.text == "Settings" for component in all_components)
    assert any(component.type == "Heading" and component.text == "Admin" for component in all_components)
    assert any(component.type == "Heading" and component.text == "Player" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Persisted: 8100" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Effective: 8000" for component in all_components)
    assert any(
        component.type == "Paragraph" and component.text == "Persisted: Not persisted" for component in all_components
    )
    assert any(component.type == "Paragraph" and component.text == "Source: file" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Pinned default" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Restart required" for component in all_components)
    assert any(
        component.type == "Paragraph"
        and component.text == "Effective: Living Room (coordinator); members: Kitchen, Living Room"
        for component in all_components
    )
    reset_forms = [
        component
        for component in all_components
        if component.type == "Form" and component.submit_url == "/api/ui/settings/admin.api.port/reset"
    ]
    assert len(reset_forms) == 1
    assert page[1].event.name == "toast-settings-success"


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_settings_edit_pages_render_select_text_and_json_fields():
    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}/edit"
    )

    select_page = route.endpoint("jukebox.reader.type")[0]
    select_form = next(component for component in walk_components(select_page.components) if component.type == "Form")
    select_field = select_form.form_fields[0]
    assert select_field.type == "FormFieldSelect"
    assert select_field.initial == "dryrun"
    assert select_field.options == [
        {"value": "dryrun", "label": "Dry Run"},
        {"value": "nfc", "label": "NFC"},
    ]

    text_page = route.endpoint("admin.ui.port")[0]
    assert any(
        component.type == "Paragraph" and component.text == "Pinned default"
        for component in walk_components(text_page.components)
    )
    text_form = next(component for component in walk_components(text_page.components) if component.type == "Form")
    text_field = text_form.form_fields[0]
    assert text_field.type == "FormFieldInput"
    assert text_field.initial == "8000"
    assert text_field.html_type == "number"

    object_page = route.endpoint("jukebox.player.sonos.selected_group")[0]
    object_form = next(component for component in walk_components(object_page.components) if component.type == "Form")
    object_field = object_form.form_fields[0]
    assert object_field.type == "FormFieldTextarea"
    assert object_field.initial == json.dumps(
        {
            "coordinator_uid": "speaker-2",
            "members": [
                {"uid": "speaker-1", "name": "Kitchen"},
                {"uid": "speaker-2", "name": "Living Room"},
            ],
        },
        indent=2,
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_settings_edit_page_renders_empty_object_field_with_placeholder_when_no_value():
    controller = build_controller()
    controller.settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    controller.settings_service.get_effective_settings_view.return_value = {
        "settings": {
            "paths": {"library_path": "~/.jukebox/library.json"},
            "admin": {"api": {"port": 8000}, "ui": {"port": 8000}},
            "jukebox": {
                "playback": {"pause_duration_seconds": 900, "pause_delay_seconds": 0.25},
                "runtime": {"loop_interval_seconds": 0.1},
                "reader": {"type": "dryrun", "nfc": {"read_timeout_seconds": 0.1}},
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
                "reader": {"type": "default", "nfc": {"read_timeout_seconds": "default"}},
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
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}/edit"
    )

    object_page = route.endpoint("jukebox.player.sonos.selected_group")[0]
    object_form = next(component for component in walk_components(object_page.components) if component.type == "Form")
    object_field = object_form.form_fields[0]

    assert object_field.type == "FormFieldTextarea"
    assert object_field.initial == ""
    assert object_field.placeholder == "Enter a JSON object. Leave blank to persist null."
    assert object_field.description.endswith(
        "Leave blank to persist null. Use Reset to remove the persisted override. Takes effect after restart."
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_setting_builds_scalar_patch_and_redirects_with_service_message():
    from discstore.adapters.inbound.ui_controller import SettingValueForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {
        "message": "Settings saved. Changes take effect after restart."
    }
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    response = await route.endpoint("admin.api.port", SettingValueForm(value="9000"))

    controller.settings_service.patch_persisted_settings.assert_called_once_with({"admin": {"api": {"port": 9000}}})
    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/settings?")
    assert "toast=toast-settings-success" in response[0].event.url
    assert "Changes+take+effect+after+restart." in response[0].event.url


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_setting_builds_object_patch_from_json_text():
    from discstore.adapters.inbound.ui_controller import SettingValueForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    response = await route.endpoint(
        "jukebox.player.sonos.selected_group",
        SettingValueForm(value='{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1","name":"Office"}]}'),
    )

    controller.settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-1",
                            "members": [{"uid": "speaker-1", "name": "Office"}],
                        }
                    }
                }
            }
        }
    )
    assert response[0].event.url.startswith("/settings?")


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_setting_treats_blank_object_text_as_none():
    from discstore.adapters.inbound.ui_controller import SettingValueForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    await route.endpoint("jukebox.player.sonos.selected_group", SettingValueForm(value=""))

    controller.settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "sonos": {
                        "selected_group": None,
                    }
                }
            }
        }
    )


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_setting_returns_field_error_for_invalid_json():
    from fastapi import HTTPException

    from discstore.adapters.inbound.ui_controller import SettingValueForm

    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("jukebox.player.sonos.selected_group", SettingValueForm(value="{"))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["value"],
                "msg": "Enter valid JSON.",
            }
        ]
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_setting_returns_field_error_for_shared_validation_failure():
    from fastapi import HTTPException

    from discstore.adapters.inbound.ui_controller import SettingValueForm
    from jukebox.settings.errors import InvalidSettingsError

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.side_effect = InvalidSettingsError("Invalid settings update.")
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("admin.api.port", SettingValueForm(value="0"))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["value"],
                "msg": "Invalid settings update.",
            }
        ]
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_reset_setting_calls_service_and_redirects():
    controller = build_controller()
    controller.settings_service.reset_persisted_value.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}/reset" and "POST" in route.methods
    )

    response = await route.endpoint("admin.api.port")

    controller.settings_service.reset_persisted_value.assert_called_once_with("admin.api.port")
    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/settings?")


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_disc_library_components_render_empty_and_editable_states():
    from discstore.adapters.inbound.ui_controller import DiscTable

    controller = build_controller()
    empty_components = controller._build_disc_library_components([])
    populated_components = controller._build_disc_library_components(
        [
            DiscTable(
                tag="tag-123",
                uri="/music/song.mp3",
                artist="Artist",
                album="Album",
                track="Track",
                shuffle=True,
            )
        ]
    )

    assert empty_components[0].type == "Paragraph"
    assert empty_components[0].text == "No disc found"
    edit_button = next(
        component
        for component in walk_components(populated_components)
        if component.type == "Button" and component.text == "Edit ✏️" and component.on_click is not None
    )
    assert edit_button.on_click.url == "/discs/tag-123/edit"


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_current_tag_banner_for_unknown_disc_offers_add_cta():
    from discstore.domain.entities import CurrentTagStatus

    controller = build_controller()

    components = controller._build_current_tag_banner_components(
        CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    )
    all_components = list(walk_components(components))
    heading = next(component for component in all_components if component.type == "Heading")
    button = next(component for component in all_components if component.type == "Button")

    assert heading.text == "Unknown disc on reader"
    assert button.text == "Add this disc"
    assert button.on_click.url == "/discs/new?prefill=current"


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_current_tag_banner_for_known_disc_is_informational_only():
    from discstore.domain.entities import CurrentTagStatus

    controller = build_controller()

    components = controller._build_current_tag_banner_components(
        CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    )
    all_components = list(walk_components(components))
    button = next(component for component in all_components if component.type == "Button")

    assert any(component.type == "Heading" and component.text == "Known disc on reader" for component in all_components)
    assert button.text == "Edit this disc"
    assert button.on_click.url == "/discs/tag-123/edit"


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_new_disc_form_components_render_blank_add_form():
    controller = build_controller()

    components = controller._build_new_disc_form_components(prefill_current=False)
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs"
    assert form.initial is None


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_new_disc_form_components_can_prefill_current_tag():
    from discstore.domain.entities import CurrentTagStatus

    controller = build_controller()
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)

    components = controller._build_new_disc_form_components(prefill_current=True)
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs"
    assert form.initial == {"tag": "tag-123", "shuffle": False}


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_edit_disc_form_components_prefill_existing_disc():
    from discstore.domain.entities import Disc, DiscMetadata, DiscOption

    controller = build_controller()
    controller.get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )

    components = controller._build_edit_disc_form_components("tag-123")
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs/tag-123"
    assert form.initial == {
        "tag": "tag-123",
        "uri": "/music/song.mp3",
        "artist": "Artist",
        "album": "Album",
        "track": "Track",
        "shuffle": True,
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_disc_form_helpers_return_errors_for_invalid_current_tag_state_or_missing_edit_target():
    from discstore.domain.entities import CurrentTagStatus

    controller = build_controller()

    controller.get_current_tag_status.execute.return_value = None
    no_tag_components = controller._build_new_disc_form_components(prefill_current=True)
    controller.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    known_tag_components = controller._build_new_disc_form_components(prefill_current=True)
    missing_tag_components = controller._build_edit_disc_form_components("")
    controller.get_disc.execute.side_effect = ValueError("Missing disc")
    missing_disc_components = controller._build_edit_disc_form_components("tag-123")

    assert no_tag_components[0].type == "Error"
    assert known_tag_components[0].type == "Error"
    assert missing_tag_components[0].type == "Error"
    assert missing_disc_components[0].type == "Error"


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_form_page_components_include_back_link_and_form():
    controller = build_controller()
    components = controller._build_form_page_components(
        title="Add disc",
        form_components=controller._build_new_disc_form_components(prefill_current=False),
    )

    page_components = list(walk_components(components))
    assert components[0].type == "Page"
    assert any(component.type == "Heading" and component.text == "Add disc" for component in page_components)
    assert any(component.type == "ModelForm" for component in page_components)
    assert any(component.type == "Link" and component.on_click.url == "/" for component in page_components)


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_current_tag_banner_event_stream_emits_serialized_updates():
    from discstore.domain.entities import CurrentTagStatus

    controller = build_controller()
    controller.get_current_tag_status.execute.side_effect = [CurrentTagStatus(tag_id="tag-123", known_in_library=False)]
    request = MagicMock()
    request.is_disconnected = AsyncMock(side_effect=[False])

    stream = controller._current_tag_banner_event_stream(request, poll_interval_seconds=0)
    # Avoid the Python 3.10+ `anext` builtin because this repo still supports Python 3.9.
    first_chunk = await stream.__anext__()

    assert first_chunk.decode("utf-8").startswith("data: [")
    assert "Unknown disc on reader" in first_chunk.decode("utf-8")


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_create_disc_returns_success_toast():
    from discstore.adapters.inbound.ui_controller import DiscForm
    from discstore.domain.entities import Disc, DiscMetadata, DiscOption

    controller = build_controller()
    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/discs")

    response = await route.endpoint(
        DiscForm(tag="tag-123", uri="/music/song.mp3", artist="Artist", album="Album", track="Track", shuffle=True)
    )

    controller.add_disc.execute.assert_called_once_with(
        "tag-123",
        Disc(
            uri="/music/song.mp3",
            metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
            option=DiscOption(shuffle=True),
        ),
    )
    assert [component.type for component in response] == ["FireEvent"]
    assert response[0].event.type == "go-to"
    assert "toast=toast-add-disc-success" in response[0].event.url


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_create_disc_returns_conflict_when_add_fails():
    from fastapi import HTTPException

    from discstore.adapters.inbound.ui_controller import DiscForm

    controller = build_controller()
    controller.add_disc.execute.side_effect = ValueError("Already existing tag")
    route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/ui/discs")

    with pytest.raises(HTTPException) as err:
        await route.endpoint(DiscForm(tag="tag-123", uri="/music/song.mp3"))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["tag"],
                "msg": "Already existing tag",
            }
        ]
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_disc_uses_edit_path():
    from discstore.adapters.inbound.ui_controller import DiscForm
    from discstore.domain.entities import DiscMetadata, DiscOption

    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}" and "POST" in route.methods
    )

    response = await route.endpoint(
        "tag-123",
        DiscForm(tag="tag-123", uri="/music/updated.mp3", artist="Artist", album="Album", track="Track", shuffle=True),
    )

    controller.edit_disc.execute.assert_called_once_with(
        tag_id="tag-123",
        uri="/music/updated.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    assert [component.type for component in response] == ["FireEvent"]
    assert "toast=toast-edit-disc-success" in response[0].event.url


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_disc_rejects_tag_changes():
    from fastapi import HTTPException

    from discstore.adapters.inbound.ui_controller import DiscForm

    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}" and "POST" in route.methods
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("tag-123", DiscForm(tag="tag-456", uri="/music/updated.mp3"))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["tag"],
                "msg": "Editing tag IDs is not supported.",
            }
        ]
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_update_disc_returns_field_error_when_edit_target_is_missing():
    from fastapi import HTTPException

    from discstore.adapters.inbound.ui_controller import DiscForm

    controller = build_controller()
    controller.edit_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='tag-123'")
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}" and "POST" in route.methods
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("tag-123", DiscForm(tag="tag-123", uri="/music/updated.mp3"))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["tag"],
                "msg": "Tag does not exist: tag_id='tag-123'",
            }
        ]
    }


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_delete_disc_endpoint_calls_remove_use_case():
    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}/delete" and "POST" in getattr(route, "methods", [])
    )

    response = await route.endpoint("tag-123")

    controller.remove_disc.execute.assert_called_once_with("tag-123")
    assert [component.type for component in response] == ["FireEvent"]
    assert response[0].event.type == "go-to"
    assert "toast=toast-remove-disc-success" in response[0].event.url


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
@pytest.mark.anyio
async def test_delete_disc_returns_404_when_disc_not_found():
    from fastapi import HTTPException

    controller = build_controller()
    controller.remove_disc.execute.side_effect = ValueError("Disc not found: tag_id='tag-456'")
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/discs/{tag_id}/delete" and "POST" in getattr(route, "methods", [])
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("tag-456")

    assert err.value.status_code == 404
    assert "Disc not found" in err.value.detail


@pytest.mark.skipif(
    sys.version_info < (3, 10) or util.find_spec("fastui") is None,
    reason="FastUI dependencies are not installed",
)
def test_index_page_shows_remove_toast():
    controller = build_controller()
    components = controller._build_index_page_components(toast="toast-remove-disc-success")
    all_components = list(walk_components(components))

    remove_toast = next(
        component for component in all_components if component.type == "Toast" and "removed" in str(component.body)
    )
    assert remove_toast.open_trigger.name == "toast-remove-disc-success"
