import importlib.util
import sys
from typing import Dict, List, Tuple, cast
from unittest.mock import MagicMock, create_autospec

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException
    from fastapi.routing import APIRoute

    from discstore.adapters.inbound.api.models import (
        DiscInput,
        DiscPatchInput,
        DiscPatchMetadataInput,
        DiscPatchOptionInput,
        SettingsPatchInput,
        SettingsResetInput,
    )
    from discstore.adapters.inbound.api_controller import (
        APIController,
        SonosSelectionInput,
    )
    from discstore.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
    from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
    from jukebox.settings.errors import InvalidSettingsError
    from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError
    from jukebox.sonos.service import InspectedSelectedSonosGroup


InvalidUidPayloadCase = Tuple[Dict[str, object], List[object], str]


INVALID_UID_PAYLOAD_CASES: List[InvalidUidPayloadCase] = [
    ({"uids": []}, [], "`uids` must include at least one UID."),
    ({"uids": ["speaker-1", "speaker-1"]}, [], "`uids` must not contain duplicate UIDs."),
]

if FASTAPI_INSTALLED:
    INVALID_UID_PAYLOAD_CASES.append(
        (
            {"uids": ["speaker-1", "speaker-2"], "coordinator_uid": ""},
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
                    name="Living Room",
                    host="192.168.1.31",
                    household_id="household-1",
                    is_visible=True,
                ),
            ],
            "Selected Sonos coordinator must be one of the selected speakers: ",
        )
    )
else:
    INVALID_UID_PAYLOAD_CASES.append(
        (
            {"uids": ["speaker-1", "speaker-2"], "coordinator_uid": ""},
            [],
            "Selected Sonos coordinator must be one of the selected speakers: ",
        )
    )


def build_controller(
    *,
    get_disc=None,
    get_current_tag_status=None,
    settings_service=None,
    sonos_service=None,
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
        sonos_service if sonos_service is not None else MagicMock(),
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


def build_inspected_group(
    resolved_members,
    coordinator_uid,
    missing_member_uids=None,
    error_message=None,
):
    coordinator = next((member for member in resolved_members if member.uid == coordinator_uid), None)
    return InspectedSelectedSonosGroup(
        coordinator=coordinator,
        resolved_members=list(resolved_members),
        missing_member_uids=list(missing_member_uids or []),
        error_message=error_message,
    )


def test_dependencies_import_failure(mocker):
    sys.modules.pop("discstore.adapters.inbound.api_controller", None)
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import discstore.adapters.inbound.api_controller  # noqa: F401

    assert "The `api_controller` module requires the optional `api` dependencies." in str(err.value)
    assert "pip install 'gukebox[api]'" in str(err.value)
    assert "uv sync --extra api" in str(err.value)
    assert "uv run --extra api jukebox-admin api" in str(err.value)


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("known_in_library", [True, False])
def test_get_current_tag_returns_current_tag_payload(known_in_library):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=known_in_library)
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-tag"),
    )

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
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/current-tag"),
    )

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
    assert ("/api/v1/current-tag/disc", ("GET",)) in route_index
    assert ("/api/v1/current-tag/disc", ("POST",)) in route_index
    assert ("/api/v1/current-tag/disc", ("PATCH",)) in route_index
    assert ("/api/v1/current-tag/disc", ("DELETE",)) in route_index


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_tag_and_disc_payload():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    get_disc = MagicMock()
    get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    controller = build_controller(get_current_tag_status=get_current_tag_status, get_disc=get_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "GET")

    response = route.endpoint()

    assert route.response_model is not None
    assert route.response_model.__name__ == "CurrentTagDiscOutput"
    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": {
            "uri": "/music/song.mp3",
            "metadata": {"artist": "Artist", "album": "Album", "track": "Track", "playlist": None},
            "option": {"shuffle": True, "is_test": False},
        },
    }
    get_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag/disc", "GET")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_404_when_current_tag_is_unknown():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag/disc", "GET")

    with pytest.raises(HTTPException) as err:
        route.endpoint()

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_created_disc_payload():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    add_disc = MagicMock()
    request = DiscInput(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    add_disc.execute.return_value = Disc(**request.model_dump())
    controller = build_controller(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "POST")

    response = route.endpoint(request)

    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": request.model_dump(),
    }
    add_disc.execute.assert_called_once_with("tag-123", Disc(**request.model_dump()))


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    add_disc = MagicMock()
    controller = build_controller(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "POST")

    response = route.endpoint(DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()))

    assert response.status_code == 204
    assert response.body == b""
    add_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_409_when_tag_exists():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    add_disc = MagicMock()
    add_disc.execute.side_effect = ValueError("Already existing tag: tag_id='tag-123'")
    controller = build_controller(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(artist="Artist"), option=DiscOption()))

    assert err.value.status_code == 409
    assert err.value.detail == "Already existing tag: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_partially_updates_existing_disc():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    edit_disc = MagicMock()
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=False),
    )
    controller = build_controller(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(
        DiscPatchInput(
            metadata=DiscPatchMetadataInput(track="Updated Track"),
            option=DiscPatchOptionInput(shuffle=False),
        )
    )

    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": {
            "uri": "/music/song.mp3",
            "metadata": {"artist": "Artist", "album": "Album", "track": "Updated Track", "playlist": None},
            "option": {"shuffle": False, "is_test": False},
        },
    }
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(track="Updated Track"),
        DiscOption(shuffle=False),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    edit_disc = MagicMock()
    controller = build_controller(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(DiscPatchInput(uri="/music/new-song.mp3"))

    assert response.status_code == 204
    assert response.body == b""
    edit_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_404_when_missing():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="missing", known_in_library=False)
    edit_disc = MagicMock()
    edit_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    controller = build_controller(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscPatchInput(uri="/music/new-song.mp3"))

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_422_when_null_assigned_to_non_nullable_option_field():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag/disc", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscPatchInput(option=DiscPatchOptionInput(shuffle=None)))

    assert err.value.status_code == 422


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_clears_nullable_metadata_field():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    edit_disc = MagicMock()
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist=None, album="Album", track="Track"),
        option=DiscOption(shuffle=False),
    )
    controller = build_controller(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(DiscPatchInput(metadata=DiscPatchMetadataInput(artist=None)))

    assert response.model_dump() == {
        "disc": {
            "metadata": {"album": "Album", "artist": None, "playlist": None, "track": "Track"},
            "option": {"is_test": False, "shuffle": False},
            "uri": "/music/song.mp3",
        },
        "tag_id": "tag-123",
    }
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(artist=None),
        None,
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_current_tag_disc_returns_no_content():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    remove_disc = MagicMock()
    controller = build_controller(get_current_tag_status=get_current_tag_status, remove_disc=remove_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "DELETE")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_current_tag_disc_returns_no_content_when_absent():
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    remove_disc = MagicMock()
    controller = build_controller(get_current_tag_status=get_current_tag_status, remove_disc=remove_disc)
    route = get_route(controller, "/api/v1/current-tag/disc", "DELETE")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_current_tag_disc_mutations_return_409_when_expected_tag_id_mismatches(method):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="other-tag", known_in_library=True)
    controller = build_controller(get_current_tag_status=get_current_tag_status)
    route = get_route(controller, "/api/v1/current-tag/disc", method)

    if method == "POST":
        call_args = (DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()), "tag-123")
    elif method == "PATCH":
        call_args = (DiscPatchInput(uri="/music/song.mp3"), "tag-123")
    else:
        call_args = ("tag-123",)

    with pytest.raises(HTTPException) as err:
        route.endpoint(*call_args)

    assert err.value.status_code == 409
    assert err.value.detail == "Current tag changed: expected_tag_id='tag-123', actual_tag_id='other-tag'"


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
    add_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
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
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=False),
    )
    controller = build_controller(edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "PATCH")

    response = route.endpoint(
        "tag-123",
        DiscPatchInput(
            metadata=DiscPatchMetadataInput(track="Updated Track"),
            option=DiscPatchOptionInput(shuffle=False),
        ),
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


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_returns_422_when_null_assigned_to_non_nullable_option_field():
    controller = build_controller()
    route = get_route(controller, "/api/v1/discs/{tag_id}", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint("tag-123", DiscPatchInput(option=DiscPatchOptionInput(shuffle=None)))

    assert err.value.status_code == 422


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
def test_patch_disc_clears_nullable_metadata_field():
    edit_disc = MagicMock()
    edit_disc.execute.return_value = "the_value_returned_by_the_EditDisc_use_case"
    controller = build_controller(edit_disc=edit_disc)
    route = get_route(controller, "/api/v1/discs/{tag_id}", "PATCH")

    response = route.endpoint("tag-123", DiscPatchInput(metadata=DiscPatchMetadataInput(artist=None)))

    assert response == "the_value_returned_by_the_EditDisc_use_case"
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(artist=None),
        None,
    )


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
def test_get_sonos_speakers_returns_normalized_discovered_speakers():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/speakers"),
    )

    response = route.endpoint()

    assert route.response_model is not None
    assert [speaker.model_dump() for speaker in response] == [
        {
            "uid": "speaker-1",
            "name": "Kitchen",
            "host": "192.168.1.30",
            "household_id": "household-1",
            "is_visible": True,
        }
    ]
    sonos_service.list_available_speakers.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_speakers_returns_empty_results():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = []
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/speakers"),
    )

    assert route.endpoint() == []
    sonos_service.list_available_speakers.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_households_groups_visible_speakers_by_household():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-2",
            is_visible=True,
        ),
        DiscoveredSonosSpeaker(
            uid="speaker-2",
            name="Living Room",
            host="192.168.1.31",
            household_id="household-2",
            is_visible=True,
        ),
        DiscoveredSonosSpeaker(
            uid="speaker-3",
            name="Bar",
            host="192.168.1.20",
            household_id="household-1",
            is_visible=True,
        ),
    ]
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/households"),
    )

    response = route.endpoint()

    assert route.response_model is not None
    assert [household.model_dump() for household in response] == [
        {
            "household_id": "household-1",
            "speakers": [
                {
                    "uid": "speaker-3",
                    "name": "Bar",
                    "host": "192.168.1.20",
                    "household_id": "household-1",
                    "is_visible": True,
                }
            ],
        },
        {
            "household_id": "household-2",
            "speakers": [
                {
                    "uid": "speaker-1",
                    "name": "Kitchen",
                    "host": "192.168.1.30",
                    "household_id": "household-2",
                    "is_visible": True,
                },
                {
                    "uid": "speaker-2",
                    "name": "Living Room",
                    "host": "192.168.1.31",
                    "household_id": "household-2",
                    "is_visible": True,
                },
            ],
        },
    ]
    sonos_service.list_available_speakers.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_households_returns_502_on_discovery_failure():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.side_effect = SonosDiscoveryError(
        "Failed to discover Sonos speakers: network unavailable"
    )
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/households"),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint()

    assert err.value.status_code == 502
    assert err.value.detail == "Failed to discover Sonos speakers: network unavailable"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_speakers_returns_502_on_discovery_failure():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.side_effect = SonosDiscoveryError(
        "Failed to discover Sonos speakers: network unavailable"
    )
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/speakers"),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint()

    assert err.value.status_code == 502
    assert err.value.detail == "Failed to discover Sonos speakers: network unavailable"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_selection_returns_not_selected_without_discovery():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    sonos_service = MagicMock()
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/selection"),
    )

    response = route.endpoint()

    assert route.response_model is not None
    assert response.model_dump() == {
        "selected_group": None,
        "availability": {
            "status": "not_selected",
            "members": [],
        },
    }
    sonos_service.inspect_selected_group.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_selection_returns_available_saved_selection():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-2",
                        "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
                    }
                }
            }
        },
    }
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
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
        ],
        coordinator_uid="speaker-2",
    )
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/selection"),
    )

    response = route.endpoint()

    assert response.model_dump() == {
        "selected_group": {
            "coordinator_uid": "speaker-2",
            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
        },
        "availability": {
            "status": "available",
            "members": [
                {
                    "uid": "speaker-1",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-1",
                        "name": "Kitchen",
                        "host": "192.168.1.30",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
                {
                    "uid": "speaker-2",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-2",
                        "name": "Living Room",
                        "host": "192.168.1.31",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
            ],
        },
    }


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_selection_returns_partially_available_saved_selection():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
                    }
                }
            }
        },
    }
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
            DiscoveredSonosSpeaker(
                uid="speaker-1",
                name="Kitchen",
                host="192.168.1.30",
                household_id="household-1",
                is_visible=True,
            )
        ],
        coordinator_uid="speaker-1",
        missing_member_uids=["speaker-2"],
    )
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/selection"),
    )

    response = route.endpoint()

    assert response.model_dump() == {
        "selected_group": {
            "coordinator_uid": "speaker-1",
            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
        },
        "availability": {
            "status": "partial",
            "members": [
                {
                    "uid": "speaker-1",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-1",
                        "name": "Kitchen",
                        "host": "192.168.1.30",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
                {
                    "uid": "speaker-2",
                    "status": "unavailable",
                    "speaker": None,
                },
            ],
        },
    }


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_selection_returns_unavailable_saved_selection_when_coordinator_is_missing():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-2",
                        "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
                    }
                }
            }
        },
    }
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
            DiscoveredSonosSpeaker(
                uid="speaker-1",
                name="Kitchen",
                host="192.168.1.30",
                household_id="household-1",
                is_visible=True,
            )
        ],
        coordinator_uid="speaker-2",
        error_message="Unable to resolve saved Sonos coordinator: speaker-2: not found on network",
    )
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/selection"),
    )

    response = route.endpoint()

    assert response.model_dump() == {
        "selected_group": {
            "coordinator_uid": "speaker-2",
            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
        },
        "availability": {
            "status": "unavailable",
            "members": [
                {
                    "uid": "speaker-1",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-1",
                        "name": "Kitchen",
                        "host": "192.168.1.30",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
                {
                    "uid": "speaker-2",
                    "status": "unavailable",
                    "speaker": None,
                },
            ],
        },
    }


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_selection_returns_502_on_discovery_failure():
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
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.side_effect = SonosDiscoveryError(
        "Failed to discover Sonos speakers: network unavailable"
    )
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/selection"),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint()

    assert err.value.status_code == 502
    assert err.value.detail == "Failed to discover Sonos speakers: network unavailable"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_sonos_selection_persists_multi_speaker_selection():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "message": "Settings saved. Changes take effect after restart.",
        "restart_required": True,
    }
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
            host="192.168.1.31",
            household_id="household-1",
            is_visible=True,
        ),
    ]
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/sonos/selection" and "PUT" in getattr(route, "methods", set())
        ),
    )

    response = route.endpoint(SonosSelectionInput(uids=["speaker-1", "speaker-2"], coordinator_uid="speaker-2"))

    assert response.model_dump() == {
        "selected_group": {
            "coordinator_uid": "speaker-2",
            "members": [{"uid": "speaker-1"}, {"uid": "speaker-2"}],
        },
        "availability": {
            "status": "available",
            "members": [
                {
                    "uid": "speaker-1",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-1",
                        "name": "Kitchen",
                        "host": "192.168.1.30",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
                {
                    "uid": "speaker-2",
                    "status": "available",
                    "speaker": {
                        "uid": "speaker-2",
                        "name": "Living Room",
                        "host": "192.168.1.31",
                        "household_id": "household-1",
                        "is_visible": True,
                    },
                },
            ],
        },
        "message": "Settings saved. Changes take effect after restart.",
        "restart_required": True,
    }
    settings_service.patch_persisted_settings.assert_called_once_with(
        {
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
            }
        }
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize(
    ("payload_data", "available_speakers", "detail"),
    INVALID_UID_PAYLOAD_CASES,
)
def test_put_sonos_selection_rejects_invalid_uid_payloads(payload_data, available_speakers, detail):
    settings_service = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = available_speakers
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/sonos/selection" and "PUT" in getattr(route, "methods", set())
        ),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint(SonosSelectionInput(**payload_data))

    assert err.value.status_code == 400
    assert err.value.detail == detail
    settings_service.patch_persisted_settings.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_sonos_selection_rejects_unknown_uid():
    settings_service = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = []
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/sonos/selection" and "PUT" in getattr(route, "methods", set())
        ),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint(SonosSelectionInput(uids=["speaker-9"]))

    assert err.value.status_code == 400
    assert err.value.detail == "Selected Sonos speakers are not currently discoverable: speaker-9"
    settings_service.patch_persisted_settings.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_sonos_selection_returns_502_on_discovery_failure():
    settings_service = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.side_effect = SonosDiscoveryError(
        "Failed to discover Sonos speakers: network unavailable"
    )
    controller = build_controller(settings_service=settings_service, sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/sonos/selection" and "PUT" in getattr(route, "methods", set())
        ),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint(SonosSelectionInput(uids=["speaker-1"]))

    assert err.value.status_code == 502
    assert err.value.detail == "Failed to discover Sonos speakers: network unavailable"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_settings_returns_sparse_settings_payload():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/settings"),
    )

    response = route.endpoint()

    assert response == {"schema_version": 1}
    settings_service.get_persisted_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_effective_settings_returns_effective_settings_payload():
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {"settings": {}, "provenance": {}, "derived": {}}
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/settings/effective"),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings" and "PATCH" in getattr(route, "methods", set())
        ),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings" and "PATCH" in getattr(route, "methods", set())
        ),
    )

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
                    "type": "pn532",
                    "pn532": {"read_timeout_seconds": 0.2},
                }
            },
        }
    }
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings" and "PATCH" in getattr(route, "methods", set())
        ),
    )

    response = route.endpoint(
        SettingsPatchInput(root={"jukebox": {"reader": {"type": "pn532", "pn532": {"read_timeout_seconds": 0.2}}}})
    )

    assert response == {
        "persisted": {
            "schema_version": 1,
            "jukebox": {
                "reader": {
                    "type": "pn532",
                    "pn532": {"read_timeout_seconds": 0.2},
                }
            },
        }
    }
    settings_service.patch_persisted_settings.assert_called_once_with(
        {"jukebox": {"reader": {"type": "pn532", "pn532": {"read_timeout_seconds": 0.2}}}}
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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings" and "PATCH" in getattr(route, "methods", set())
        ),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings" and "PATCH" in getattr(route, "methods", set())
        ),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

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
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

    response = route.endpoint(SettingsResetInput(path="jukebox.player.sonos.selected_group"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.player.sonos.selected_group")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_reader_override():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "pn532"}}}
    }
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

    response = route.endpoint(SettingsResetInput(path="jukebox.reader.pn532.read_timeout_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "pn532"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.reader.pn532.read_timeout_seconds")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_accepts_section_path():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {"persisted": {"schema_version": 1}}
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

    response = route.endpoint(SettingsResetInput(path="admin"))

    assert response == {"persisted": {"schema_version": 1}}
    settings_service.reset_persisted_value.assert_called_once_with("admin")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_returns_400_for_invalid_reset_path():
    settings_service = MagicMock()
    settings_service.reset_persisted_value.side_effect = InvalidSettingsError("Unsupported settings path")
    controller = build_controller(settings_service=settings_service)
    route = cast(
        APIRoute,
        next(
            route
            for route in controller.app.routes
            if getattr(route, "path", None) == "/api/v1/settings/reset" and "POST" in getattr(route, "methods", set())
        ),
    )

    with pytest.raises(HTTPException) as err:
        route.endpoint(SettingsResetInput(path="jukebox.reader.serial_port"))

    assert err.value.status_code == 400
    assert err.value.detail == "Unsupported settings path"
