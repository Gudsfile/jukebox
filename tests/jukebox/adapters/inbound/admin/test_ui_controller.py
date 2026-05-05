import sys
from importlib import util
from unittest.mock import MagicMock, create_autospec

import pytest

FASTUI_INSTALLED = util.find_spec("fastui") is not None


def build_speaker(uid, name, host, household_id):
    from jukebox.sonos.discovery import DiscoveredSonosSpeaker

    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def test_dependencies_import_failure(mocker):
    sys.modules.pop("jukebox.adapters.inbound.admin.ui_controller", None)
    mocker.patch.dict("sys.modules", {"fastui": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import jukebox.adapters.inbound.admin.ui_controller  # noqa: F401

    assert "The `ui_controller` module requires the optional `ui` dependencies." in str(err.value)
    assert "pip install 'gukebox[ui]'" in str(err.value)
    assert "uv sync --extra ui" in str(err.value)
    assert "uv run --extra ui jukebox-admin ui" in str(err.value)


def build_controller():
    from jukebox.adapters.inbound.admin.ui_controller import UIController
    from jukebox.sonos.service import InspectedSelectedSonosGroup, SonosService

    settings_service = MagicMock()
    sonos_service = create_autospec(SonosService)
    available_speakers = [
        build_speaker(uid="speaker-1", name="Kitchen", host="192.168.1.30", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-1"),
    ]
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
    sonos_service.list_network_speakers.return_value = available_speakers
    sonos_service.inspect_selected_group.return_value = InspectedSelectedSonosGroup(
        coordinator=available_speakers[1],
        resolved_members=list(available_speakers),
        missing_member_uids=[],
        error_message=None,
    )

    return UIController(
        add_disc=MagicMock(),
        list_discs=MagicMock(),
        remove_disc=MagicMock(),
        edit_disc=MagicMock(),
        get_disc=MagicMock(),
        get_current_tag_status=MagicMock(),
        settings_service=settings_service,
        sonos_service=sonos_service,
    )


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_ui_controller_registers_routes():
    controller = build_controller()

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
    assert ("/api/ui/sonos", ("GET",)) in route_index
    assert ("/api/ui/sonos/edit", ("GET",)) in route_index
    assert ("/api/ui/sonos/edit", ("POST",)) in route_index
    assert ("/api/ui/sonos/reset", ("POST",)) in route_index
    assert ("/api/v1/discs", ("GET",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("GET",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("POST",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("PATCH",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("DELETE",)) in route_index
    assert ("/api/v1/current-tag", ("GET",)) in route_index

    html_route = next(route for route in controller.app.routes if getattr(route, "path", None) == "/{path:path}")
    html_response = html_route.endpoint("discs/new")
    assert html_response.status_code == 200
    assert "/api/ui" in html_response.body.decode("utf-8")


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_sonos_selection_saves_and_redirects():
    from jukebox.adapters.inbound.admin.ui_controller import SonosSelectionForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {
        "message": "Settings saved. Changes take effect after restart."
    }
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/sonos/edit" and "POST" in route.methods
    )

    response = await route.endpoint(SonosSelectionForm(uids=["speaker-1", "speaker-2"], coordinator_uid="speaker-2"))

    controller.settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {
                        "selected_group": {
                            "household_id": "household-1",
                            "coordinator_uid": "speaker-2",
                            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
                        }
                    },
                }
            }
        }
    )
    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/sonos?")
    assert "toast=toast-sonos-success" in response[0].event.url
    assert "Changes+take+effect+after+restart." in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_sonos_selection_returns_field_error_for_invalid_coordinator():
    from jukebox.adapters.inbound.admin.ui_controller import SonosSelectionForm

    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/sonos/edit" and "POST" in route.methods
    )

    response = await route.endpoint(SonosSelectionForm(uids=["speaker-1"], coordinator_uid="speaker-2"))

    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/sonos/edit?")
    assert (
        "error_message=Selected+Sonos+coordinator+must+be+one+of+the+selected+speakers%3A+Living+Room+%5Bspeaker-2%5D"
        in response[0].event.url
    )
    assert "uids=speaker-1" in response[0].event.url
    assert "coordinator_uid=speaker-2" in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_sonos_selection_saves_single_speaker_selection():
    from jukebox.adapters.inbound.admin.ui_controller import SonosSelectionForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/sonos/edit" and "POST" in route.methods
    )

    response = await route.endpoint(SonosSelectionForm(uids="speaker-1", coordinator_uid="speaker-1"))  # ty: ignore[invalid-argument-type] # field_validator coerces str to list[str] at runtime

    controller.settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {
                        "selected_group": {
                            "household_id": "household-1",
                            "coordinator_uid": "speaker-1",
                            "members": [{"uid": "speaker-1"}],
                        }
                    },
                }
            }
        }
    )
    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/sonos?")


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_sonos_selection_redirects_when_write_succeeds_but_effective_settings_stay_invalid():
    from jukebox.adapters.inbound.admin.ui_controller import SonosSelectionForm
    from jukebox.settings.errors import InvalidSettingsError

    controller = build_controller()

    def raise_after_persist(patch):
        del patch
        controller.settings_service.get_persisted_settings_view.return_value = {
            "schema_version": 1,
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-2",
                            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
                        }
                    },
                }
            },
        }
        raise InvalidSettingsError("Invalid effective settings after environment overrides.")

    controller.settings_service.patch_persisted_settings.side_effect = raise_after_persist
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/sonos/edit" and "POST" in route.methods
    )

    response = await route.endpoint(SonosSelectionForm(uids=["speaker-1", "speaker-2"], coordinator_uid="speaker-2"))

    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/sonos?")
    assert "toast=toast-sonos-success" in response[0].event.url
    assert "effective+settings+are+still+unavailable" in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_reset_sonos_selection_calls_service_and_redirects():
    controller = build_controller()
    controller.settings_service.reset_persisted_value.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/sonos/reset" and "POST" in route.methods
    )

    response = await route.endpoint()

    controller.settings_service.reset_persisted_value.assert_called_once_with("jukebox.player.sonos.selected_group")
    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/sonos?")
    assert "toast=toast-sonos-success" in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_builds_scalar_patch_and_redirects_with_service_message():
    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_builds_object_patch_from_json_text():
    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm

    controller = build_controller()
    controller.settings_service.patch_persisted_settings.return_value = {"message": "Settings saved."}
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    response = await route.endpoint(
        "jukebox.player.sonos.selected_group",
        SettingValueForm(value='{"coordinator_uid":"speaker-1","members":[{"uid":"speaker-1"}]}'),
    )

    controller.settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-1",
                            "members": [{"uid": "speaker-1"}],
                        }
                    }
                }
            }
        }
    )
    assert response[0].event.url.startswith("/settings?")


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_treats_blank_object_text_as_none():
    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_returns_field_error_for_invalid_json():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_returns_field_error_for_non_object_json():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm

    controller = build_controller()
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    with pytest.raises(HTTPException) as err:
        await route.endpoint("jukebox.player.sonos.selected_group", SettingValueForm(value='["speaker-1"]'))

    assert err.value.status_code == 422
    assert err.value.detail == {
        "form": [
            {
                "loc": ["value"],
                "msg": "Enter a JSON object.",
            }
        ]
    }


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_redirects_when_write_succeeds_but_effective_settings_stay_invalid():
    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm
    from jukebox.settings.errors import InvalidSettingsError

    controller = build_controller()

    def raise_after_persist(patch):
        controller.settings_service.get_persisted_settings_view.return_value = {
            "schema_version": 1,
            "admin": {"api": {"port": 9000}, "ui": {"port": 8000}},
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
        }
        raise InvalidSettingsError("Invalid effective settings after environment overrides.")

    controller.settings_service.patch_persisted_settings.side_effect = raise_after_persist
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}" and "POST" in route.methods
    )

    response = await route.endpoint("admin.api.port", SettingValueForm(value="9000"))

    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/settings?")
    assert "toast=toast-settings-success" in response[0].event.url
    assert "effective+settings+are+still+unavailable" in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_setting_returns_field_error_for_shared_validation_failure():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import SettingValueForm
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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_reset_setting_redirects_when_reset_succeeds_but_effective_settings_stay_invalid():
    from jukebox.settings.errors import InvalidSettingsError

    controller = build_controller()

    def raise_after_reset(setting_path):
        del setting_path
        controller.settings_service.get_persisted_settings_view.return_value = {
            "schema_version": 1,
            "admin": {"ui": {"port": 8000}},
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
        }
        raise InvalidSettingsError("Invalid effective settings after environment overrides.")

    controller.settings_service.reset_persisted_value.side_effect = raise_after_reset
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}/reset" and "POST" in route.methods
    )

    response = await route.endpoint("admin.api.port")

    assert response[0].type == "FireEvent"
    assert response[0].event.url.startswith("/settings?")
    assert "toast=toast-settings-success" in response[0].event.url
    assert "effective+settings+are+still+unavailable" in response[0].event.url


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_reset_setting_calls_service_and_returns_refreshed_settings_page():
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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_reset_setting_rerenders_edit_page_with_visible_error(walk_components):
    from jukebox.settings.errors import InvalidSettingsError

    controller = build_controller()
    controller.settings_service.reset_persisted_value.side_effect = InvalidSettingsError("Invalid settings update.")
    route = next(
        route
        for route in controller.app.routes
        if getattr(route, "path", None) == "/api/ui/settings/{setting_path}/reset" and "POST" in route.methods
    )

    response = await route.endpoint("admin.api.port")
    all_components = list(walk_components(response[0].components))

    controller.settings_service.reset_persisted_value.assert_called_once_with("admin.api.port")
    assert response[0].type == "Page"
    assert any(
        component.type == "Error"
        and component.title == "Reset failed"
        and component.description == "Invalid settings update."
        for component in all_components
    )


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_ui_controller_does_not_register_get_reset_setting_route():
    controller = build_controller()

    assert not any(
        getattr(route, "path", None) == "/api/ui/settings/{setting_path}/reset"
        and "GET" in getattr(route, "methods", set())
        for route in controller.app.routes
    )


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_create_disc_returns_success_toast():
    from jukebox.adapters.inbound.admin.ui_controller import DiscForm
    from jukebox.domain.entities import Disc, DiscMetadata, DiscOption

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_create_disc_returns_conflict_when_add_fails():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import DiscForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_disc_uses_edit_path():
    from jukebox.adapters.inbound.admin.ui_controller import DiscForm
    from jukebox.domain.entities import DiscMetadata, DiscOption

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_disc_rejects_tag_changes():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import DiscForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_update_disc_returns_field_error_when_edit_target_is_missing():
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.ui_controller import DiscForm

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_form_parsing_does_not_lack_python_multipart():
    """Verify that python-multipart is installed.

    Without it, FastAPI raises: "The `python-multipart` library must be installed to use
    form parsing in the UI.
    """
    from starlette.requests import Request

    scope = {"type": "http", "headers": []}
    request = Request(scope)

    try:
        await request.form()
    except RuntimeError as e:
        assert "python-multipart" not in str(e)
        raise
