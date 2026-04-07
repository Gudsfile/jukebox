import importlib.util
import sys
from typing import cast
from unittest.mock import MagicMock, create_autospec

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException
    from fastapi.routing import APIRoute

    from discstore.adapters.inbound.api_controller import (
        APIController,
        DiscInput,
        DiscPatchInput,
        SettingsPatchInput,
        SettingsResetInput,
    )
    from discstore.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
    from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
    from jukebox.settings.errors import InvalidSettingsError


def build_controller(
    *,
    get_disc=None,
    get_current_tag_status=None,
    settings_service=None,
    add_disc=None,
    list_discs=None,
    remove_disc=None,
    edit_disc=None,
):
    return APIController(
        add_disc if add_disc is not None else MagicMock(),
        list_discs if list_discs is not None else MagicMock(),
        remove_disc if remove_disc is not None else MagicMock(),
        edit_disc if edit_disc is not None else MagicMock(),
        get_disc if get_disc is not None else MagicMock(),
        get_current_tag_status if get_current_tag_status is not None else MagicMock(),
        settings_service if settings_service is not None else MagicMock(),
    )


def get_route(controller, path, method):
    return cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
        ),
    )


def test_dependencies_import_failure(mocker):
    sys.modules.pop("discstore.adapters.inbound.api_controller", None)
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert "The `api_controller` module requires the optional `api` dependencies." in str(err.value)
    assert "pip install 'gukebox[api]'" in str(err.value)
    assert "uv sync --extra api" in str(err.value)
    assert "uv run --extra api discstore api" in str(err.value)


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("known_in_library", [True, False])
def test_get_current_tag_returns_current_tag_payload(known_in_library):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=known_in_library)
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag", "GET")

    response = route.endpoint()

    assert route.response_model is not None
    assert route.response_model.__name__ == "CurrentTagStatusOutput"
    assert response.model_dump() == {"tag_id": "tag-123", "known_in_library": known_in_library}
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag", "GET")

    response = route.endpoint()

    assert 204 in route.responses
    assert response.status_code == 204
    assert response.body == b""
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_disc_routes_register_explicit_crud_paths():
    controller = build_controller()

    route_index = {
        (getattr(route, "path", None), tuple(sorted(getattr(route, "methods", []))))
        for route in controller.app.routes
        if hasattr(route, "path")
    }

    assert ("/api/v1/discs", ("GET",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("GET",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("POST",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("PATCH",)) in route_index
    assert ("/api/v1/discs/{tag_id}", ("DELETE",)) in route_index
    assert ("/api/v1/disc", ("POST",)) not in route_index
    assert ("/api/v1/disc", ("DELETE",)) not in route_index


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_disc_returns_disc_payload():
    get_disc = MagicMock()
    get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    controller = build_controller(get_disc=get_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "GET")

    response = route.endpoint("tag-123")

    assert route.response_model is not None
    assert route.response_model.__name__ == "DiscOutput"
    assert response.model_dump() == {
        "uri": "/music/song.mp3",
        "metadata": {"artist": "Artist", "album": "Album", "track": "Track", "playlist": None},
        "option": {"shuffle": True, "is_test": False},
    }
    get_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_disc_returns_404_when_missing():
    get_disc = MagicMock()
    get_disc.execute.side_effect = ValueError("Tag not found: tag_id='missing'")
    controller = build_controller(get_disc=get_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "GET")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing")

    assert err.value.status_code == 404
    assert err.value.detail == "Tag not found: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_disc_returns_created_disc_payload():
    add_disc = MagicMock()
    controller = build_controller(add_disc=add_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "POST")
    request = DiscInput(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )

    response = route.endpoint("tag-123", request)

    assert response.model_dump() == request.model_dump()
    add_disc.execute.assert_called_once_with("tag-123", Disc(**request.model_dump()))


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_disc_returns_409_when_tag_exists():
    add_disc = MagicMock()
    add_disc.execute.side_effect = ValueError("Already existing tag: tag_id='tag-123'")
    controller = build_controller(add_disc=add_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(
            "tag-123",
            DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(artist="Artist"), option=DiscOption()),
        )

    assert err.value.status_code == 409
    assert err.value.detail == "Already existing tag: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_partially_updates_existing_disc():
    edit_disc = MagicMock()
    get_disc = MagicMock()
    get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=False),
    )
    controller = build_controller(edit_disc=edit_disc, get_disc=get_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "PATCH")

    response = route.endpoint(
        "tag-123",
        DiscPatchInput(metadata={"track": "Updated Track"}, option={"shuffle": False}),
    )

    assert response.model_dump() == {
        "uri": "/music/song.mp3",
        "metadata": {"artist": "Artist", "album": "Album", "track": "Updated Track", "playlist": None},
        "option": {"shuffle": False, "is_test": False},
    }
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(track="Updated Track"),
        DiscOption(shuffle=False),
    )
    get_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_returns_404_when_missing():
    edit_disc = MagicMock()
    edit_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    controller = build_controller(edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing", DiscPatchInput(uri="/music/new-song.mp3"))

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_disc_returns_no_content():
    remove_disc = MagicMock()
    controller = build_controller(remove_disc=remove_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "DELETE")

    response = route.endpoint("tag-123")

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_disc_returns_404_when_missing():
    remove_disc = MagicMock()
    remove_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    controller = build_controller(remove_disc=remove_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "DELETE")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing")

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_settings_returns_sparse_settings_payload():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "GET")

    response = route.endpoint()

    assert response == {"schema_version": 1}
    settings_service.get_persisted_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_effective_settings_returns_effective_settings_payload():
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {"settings": {}, "provenance": {}, "derived": {}}
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/effective", "GET")

    response = route.endpoint()

    assert response == {"settings": {}, "provenance": {}, "derived": {}}
    settings_service.get_effective_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_persisted_settings():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "PATCH")

    response = route.endpoint(SettingsPatchInput(root={"admin": {"api": {"port": 9000}}}))

    assert response == {"persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}}
    settings_service.patch_persisted_settings.assert_called_once_with({"admin": {"api": {"port": 9000}}})


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_playback_timing_settings():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "PATCH")

    response = route.endpoint(SettingsPatchInput(root={"jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}}
    settings_service.patch_persisted_settings.assert_called_once_with(
        {"jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_reader_settings():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {
            "schema_version": 1,
            "jukebox": {
                "reader": {
                    "type": "nfc",
                    "nfc": {"read_timeout_seconds": 0.2},
                }
            },
        }
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "PATCH")

    response = route.endpoint(
        SettingsPatchInput(root={"jukebox": {"reader": {"type": "nfc", "nfc": {"read_timeout_seconds": 0.2}}}})
    )

    assert response == {
        "persisted": {
            "schema_version": 1,
            "jukebox": {
                "reader": {
                    "type": "nfc",
                    "nfc": {"read_timeout_seconds": 0.2},
                }
            },
        }
    }
    settings_service.patch_persisted_settings.assert_called_once_with(
        {"jukebox": {"reader": {"type": "nfc", "nfc": {"read_timeout_seconds": 0.2}}}}
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_player_settings():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {
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
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "PATCH")

    response = route.endpoint(
        SettingsPatchInput(
            root={
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
                }
            }
        )
    )

    assert response == {
        "persisted": {
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
    }
    settings_service.patch_persisted_settings.assert_called_once_with(
        {
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
            }
        }
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_returns_400_for_invalid_settings_write():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.side_effect = InvalidSettingsError("Unsupported settings path")
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(SettingsPatchInput(root={"jukebox": {"reader": {"serial": {"path": "/dev/ttyUSB0"}}}}))

    assert err.value.status_code == 400
    assert err.value.detail == "Unsupported settings path"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_route_generates_openapi_schema():
    controller = build_controller()

    schema = controller.app.openapi()

    assert "/api/v1/settings" in schema["paths"]


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_persisted_override():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "admin": {"ui": {"port": 9200}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="admin.api.port"))

    assert response == {"persisted": {"schema_version": 1, "admin": {"ui": {"port": 9200}}}}
    settings_service.reset_persisted_value.assert_called_once_with("admin.api.port")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_playback_timing_override():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"playback": {"pause_duration_seconds": 600}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.runtime.loop_interval_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"playback": {"pause_duration_seconds": 600}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.runtime.loop_interval_seconds")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_selected_group_override():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.player.sonos.selected_group"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.player.sonos.selected_group")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_reader_override():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "nfc"}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.reader.nfc.read_timeout_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "nfc"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.reader.nfc.read_timeout_seconds")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_accepts_section_path():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {"persisted": {"schema_version": 1}}
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="admin"))

    assert response == {"persisted": {"schema_version": 1}}
    settings_service.reset_persisted_value.assert_called_once_with("admin")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_returns_400_for_invalid_reset_path():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.side_effect = InvalidSettingsError("Unsupported settings path")
    controller = build_controller(settings_service=settings_service)
    route = get_route(controller, "/api/v1/settings/reset", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(SettingsResetInput(path="jukebox.reader.serial_port"))

    assert err.value.status_code == 400
    assert err.value.detail == "Unsupported settings path"
