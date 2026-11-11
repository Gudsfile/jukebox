import importlib.util
from unittest.mock import MagicMock

import pytest

from jukebox.settings.entities import AppSettings
from jukebox.settings.errors import ErrorCode, InvalidSettingsError

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.pn532_router import build_pn532_router


def build_settings(pn532: dict) -> AppSettings:
    return AppSettings.model_validate({"jukebox": {"reader": {"pn532": pn532}}})


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_pn532_returns_effective_config_merging_profile_defaults_with_overrides(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.return_value = build_settings(
        {"board_profile": "waveshare_hat", "spi": {"cs": 8}}
    )
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "GET")

    response = route.endpoint()

    assert response.board_profile == "waveshare_hat"
    assert response.protocol == "spi"
    assert response.overrides.model_dump() == {"reset": None, "cs": 8, "irq": None}
    assert response.resolved.model_dump() == {"reset": 20, "cs": 8, "irq": None}


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_pn532_lists_every_profile_with_its_default_pins(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.return_value = build_settings({})
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "GET")

    response = route.endpoint()

    assert [
        (profile.name, profile.label, profile.protocol, profile.defaults.model_dump()) for profile in response.profiles
    ] == [
        ("waveshare_hat", "WaveShare PN532 NFC HAT", "spi", {"reset": 20, "cs": 4, "irq": None}),
        ("hiletgo_v3", "HiLetgo PN532 V3", "spi", {"reset": None, "cs": 4, "irq": None}),
        ("custom", "Custom", "spi", {"reset": None, "cs": None, "irq": None}),
    ]


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_pn532_maps_invalid_effective_settings_to_500(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.side_effect = InvalidSettingsError(
        "Invalid effective settings", code=ErrorCode.INVALID_EFFECTIVE
    )
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "GET")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 500
    assert "Invalid effective settings" in exc_info.value.detail
