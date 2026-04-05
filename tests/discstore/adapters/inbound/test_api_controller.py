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
        SettingsPatchInput,
        SettingsResetInput,
        SonosSelectionInput,
    )
    from discstore.domain.entities import CurrentTagStatus
    from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
    from jukebox.settings.errors import InvalidSettingsError
    from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError


def build_controller(
    *,
    get_current_tag_status=None,
    settings_service=None,
    sonos_service=None,
):
    return APIController(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        get_current_tag_status or MagicMock(),
        settings_service or MagicMock(),
        sonos_service or MagicMock(),
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
    sonos_service.list_available_speakers.assert_not_called()


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
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]
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
    sonos_service.list_available_speakers.return_value = [
        DiscoveredSonosSpeaker(
            uid="speaker-1",
            name="Kitchen",
            host="192.168.1.30",
            household_id="household-1",
            is_visible=True,
        )
    ]
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
    sonos_service.list_available_speakers.side_effect = SonosDiscoveryError(
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
    ("payload_data", "detail"),
    [
        ({"uids": []}, "`uids` must include at least one UID."),
        ({"uids": ["speaker-1", "speaker-1"]}, "`uids` must not contain duplicate UIDs."),
    ],
)
def test_put_sonos_selection_rejects_invalid_uid_payloads(payload_data, detail):
    settings_service = MagicMock()
    sonos_service = MagicMock()
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
                    "type": "nfc",
                    "nfc": {"read_timeout_seconds": 0.2},
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
        "persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "nfc"}}}
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

    response = route.endpoint(SettingsResetInput(path="jukebox.reader.nfc.read_timeout_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "nfc"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.reader.nfc.read_timeout_seconds")


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
