import importlib.util
from unittest.mock import MagicMock

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.models import SettingsPatchInput, SettingsResetInput
    from jukebox.adapters.inbound.admin.api.settings_router import build_settings_router
    from jukebox.settings.errors import ErrorCode, InvalidSettingsError


def build_router(*, settings_service=None):
    return build_settings_router(
        settings_service=settings_service if settings_service is not None else MagicMock(),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_settings_returns_sparse_settings_payload(get_route):
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "GET")

    response = route.endpoint()

    assert response == {"schema_version": 1}
    settings_service.get_persisted_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_effective_settings_returns_effective_settings_payload(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings_view.return_value = {"settings": {}, "provenance": {}, "derived": {}}
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/effective", "GET")

    response = route.endpoint()

    assert response == {"settings": {}, "provenance": {}, "derived": {}}
    settings_service.get_effective_settings_view.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_persisted_settings(get_route):
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "PATCH")

    response = route.endpoint(SettingsPatchInput(root={"admin": {"api": {"port": 9000}}}))

    assert response == {"persisted": {"schema_version": 1, "admin": {"api": {"port": 9000}}}}
    settings_service.patch_persisted_settings.assert_called_once_with({"admin": {"api": {"port": 9000}}})


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_playback_timing_settings(get_route):
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "PATCH")

    response = route.endpoint(SettingsPatchInput(root={"jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}}
    settings_service.patch_persisted_settings.assert_called_once_with(
        {"jukebox": {"runtime": {"loop_interval_seconds": 0.2}}}
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_settings_updates_reader_settings(get_route):
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
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "PATCH")

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
def test_patch_settings_updates_player_settings(get_route):
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
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "PATCH")

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
def test_patch_settings_returns_400_for_invalid_settings_write(get_route):
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.side_effect = InvalidSettingsError(
        "Unsupported settings path", code=ErrorCode.UNSUPPORTED_PATH
    )
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(SettingsPatchInput(root={"jukebox": {"reader": {"serial": {"path": "/dev/ttyUSB0"}}}}))

    assert err.value.status_code == 400
    assert err.value.detail == "Unsupported settings path"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_persisted_override(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "admin": {"ui": {"port": 9200}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="admin.api.port"))

    assert response == {"persisted": {"schema_version": 1, "admin": {"ui": {"port": 9200}}}}
    settings_service.reset_persisted_value.assert_called_once_with("admin.api.port")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_playback_timing_override(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"playback": {"pause_duration_seconds": 600}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.runtime.loop_interval_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"playback": {"pause_duration_seconds": 600}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.runtime.loop_interval_seconds")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_selected_group_override(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.player.sonos.selected_group"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"player": {"type": "sonos"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.player.sonos.selected_group")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_removes_reader_override(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {
        "persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "pn532"}}}
    }
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="jukebox.reader.pn532.read_timeout_seconds"))

    assert response == {"persisted": {"schema_version": 1, "jukebox": {"reader": {"type": "pn532"}}}}
    settings_service.reset_persisted_value.assert_called_once_with("jukebox.reader.pn532.read_timeout_seconds")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_accepts_section_path(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.return_value = {"persisted": {"schema_version": 1}}
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    response = route.endpoint(SettingsResetInput(path="admin"))

    assert response == {"persisted": {"schema_version": 1}}
    settings_service.reset_persisted_value.assert_called_once_with("admin")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_reset_settings_returns_400_for_invalid_reset_path(get_route):
    settings_service = MagicMock()
    settings_service.reset_persisted_value.side_effect = InvalidSettingsError(
        "Unsupported settings path", code=ErrorCode.UNSUPPORTED_PATH
    )
    router = build_router(settings_service=settings_service)
    route = get_route(router, "/api/v1/settings/reset", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(SettingsResetInput(path="jukebox.reader.serial_port"))

    assert err.value.status_code == 400
    assert err.value.detail == "Unsupported settings path"
