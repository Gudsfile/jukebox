import importlib.util
import sys
from typing import cast
from unittest.mock import MagicMock

import pytest

from jukebox.shared.errors import MissingOptionalDependencyError

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException
    from fastapi.routing import APIRoute

    from jukebox.adapters.inbound.admin.api_controller import (
        APIController,
        SonosSelectionInput,
    )
    from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError
    from jukebox.sonos.service import InspectedSelectedSonosGroup

InvalidUidPayloadCase = tuple[dict[str, object], list[object], str]


INVALID_UID_PAYLOAD_CASES: list[InvalidUidPayloadCase] = [
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
    sys.modules.pop("jukebox.adapters.inbound.admin.api_controller", None)
    mocker.patch.dict("sys.modules", {"fastapi": None})

    with pytest.raises(MissingOptionalDependencyError) as err:
        import jukebox.adapters.inbound.admin.api_controller  # noqa: F401

    assert "The `api_controller` module requires the optional `api` dependencies." in str(err.value)
    assert "pip install 'gukebox[api]'" in str(err.value)
    assert "uv sync --extra api" in str(err.value)
    assert "uv run --extra api jukebox-admin api" in str(err.value)


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
def test_patch_settings_route_generates_openapi_schema():
    controller = build_controller()

    schema = controller.app.openapi()

    assert "/api/v1/settings" in schema["paths"]


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_speakers_returns_normalized_discovered_speakers():
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
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
    sonos_service.list_network_speakers.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_speakers_returns_empty_results():
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = []
    controller = build_controller(sonos_service=sonos_service)
    route = cast(
        APIRoute,
        next(route for route in controller.app.routes if getattr(route, "path", None) == "/api/v1/sonos/speakers"),
    )

    assert route.endpoint() == []
    sonos_service.list_network_speakers.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_sonos_speakers_returns_502_on_discovery_failure():
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.side_effect = SonosDiscoveryError(
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
                        "household_id": "household-1",
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
            "household_id": "household-1",
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
                        "household_id": "household-1",
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
            "household_id": "household-1",
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
                        "household_id": "household-1",
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
            "household_id": "household-1",
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
                        "household_id": "household-1",
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
    sonos_service.list_network_speakers.return_value = [
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
            "household_id": "household-1",
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
                            "household_id": "household-1",
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
    sonos_service.list_network_speakers.return_value = available_speakers
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
    sonos_service.list_network_speakers.return_value = []
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
    sonos_service.list_network_speakers.side_effect = SonosDiscoveryError(
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
