import importlib.util
from unittest.mock import MagicMock, call

import pytest
from pydantic import ValidationError

from jukebox.pn532.profiles import SpiConnectionParams
from jukebox.settings.entities import AppSettings
from jukebox.settings.errors import ErrorCode, InvalidSettingsError
from jukebox.shared.errors import MissingOptionalDependencyError

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.pn532_router import Pn532ConfigInput, build_pn532_router


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


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_pn532_persists_profile_and_only_pins_that_differ_from_profile_defaults(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.return_value = build_settings(
        {"board_profile": "waveshare_hat", "spi": {"cs": 8}}
    )
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "PUT")

    route.endpoint(Pn532ConfigInput(board_profile="waveshare_hat", spi={"reset": 20, "cs": 8, "irq": None}))

    assert settings_service.method_calls[:5] == [
        call.set_persisted_value("jukebox.reader.pn532.board_profile", "waveshare_hat"),
        call.reset_persisted_value("jukebox.reader.pn532.protocol"),
        call.reset_persisted_value("jukebox.reader.pn532.spi.reset"),
        call.set_persisted_value("jukebox.reader.pn532.spi.cs", "8"),
        call.reset_persisted_value("jukebox.reader.pn532.spi.irq"),
    ]


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_pn532_returns_the_updated_effective_config(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.return_value = build_settings({"board_profile": "hiletgo_v3"})
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "PUT")

    response = route.endpoint(
        Pn532ConfigInput(board_profile="hiletgo_v3", spi={"reset": None, "cs": None, "irq": None})
    )

    assert response.board_profile == "hiletgo_v3"
    assert response.resolved.model_dump() == {"reset": None, "cs": 4, "irq": None}


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_put_pn532_maps_settings_errors_to_400(get_route):
    settings_service = MagicMock()
    settings_service.set_persisted_value.side_effect = InvalidSettingsError(
        "Invalid settings update", code=ErrorCode.INVALID_UPDATE
    )
    route = get_route(build_pn532_router(settings_service), "/api/v1/pn532", "PUT")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint(Pn532ConfigInput(board_profile="custom", spi={"reset": 25, "cs": 8, "irq": None}))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid settings update"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_pn532_config_input_rejects_unknown_profiles_and_negative_pins():
    with pytest.raises(ValidationError):
        Pn532ConfigInput.model_validate({"board_profile": "nope", "spi": {"reset": None, "cs": None, "irq": None}})
    with pytest.raises(ValidationError):
        Pn532ConfigInput.model_validate({"board_profile": "custom", "spi": {"reset": -1, "cs": None, "irq": None}})


def _make_reader(firmware_version=(1, 6), uid=None):
    mock_reader = MagicMock()
    mock_reader.firmware_version = firmware_version
    mock_reader.read.return_value = uid
    return MagicMock(return_value=mock_reader)


def _failing_builder(error: Exception):
    def build(**_kwargs):
        raise error

    return build


def _probe_route(get_route, build_pn532_reader, pn532: dict | None = None):
    settings_service = MagicMock()
    settings_service.get_effective_settings.return_value = build_settings(
        pn532 if pn532 is not None else {"board_profile": "waveshare_hat", "spi": {"cs": 8}}
    )
    return get_route(build_pn532_router(settings_service, build_pn532_reader), "/api/v1/pn532/probe", "POST")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_returns_setup_firmware_and_uid(get_route):
    build_fn = _make_reader(firmware_version=(1, 6), uid="04:ab:cd:ef")
    route = _probe_route(get_route, build_fn)

    response = route.endpoint()

    assert response.model_dump() == {
        "board_profile": "waveshare_hat",
        "protocol": "spi",
        "pins": {"reset": 20, "cs": 8, "irq": None},
        "firmware_version": "1.6",
        "uid": "04:ab:cd:ef",
    }
    assert build_fn.call_args.kwargs["connection"] == SpiConnectionParams(reset=20, cs=8, irq=None)


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_returns_no_uid_without_tag(get_route):
    route = _probe_route(get_route, _make_reader(uid=None))

    assert route.endpoint().uid is None


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_maps_missing_extra_to_501_with_install_hint(get_route):
    error = MissingOptionalDependencyError("The `pn532` reader", "pn532", "jukebox ...")
    route = _probe_route(get_route, _failing_builder(error))

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 501
    assert "pip install 'gukebox[pn532]'" in exc_info.value.detail


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_maps_gpio_errors_to_502_with_hint(get_route):
    route = _probe_route(get_route, _failing_builder(OSError("bad GPIO number")))

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail.startswith("GPIO error — your pin configuration may be incorrect (bad GPIO number).")
    assert "Check the board profile and pins" in exc_info.value.detail


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_maps_other_reader_errors_to_502(get_route):
    error = RuntimeError("SPI interface not enabled. Use raspi-config to enable it.")
    route = _probe_route(get_route, _failing_builder(error))

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "PN532 error: SPI interface not enabled. Use raspi-config to enable it."


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_maps_invalid_effective_settings_to_500(get_route):
    settings_service = MagicMock()
    settings_service.get_effective_settings.side_effect = InvalidSettingsError(
        "Invalid effective settings", code=ErrorCode.INVALID_EFFECTIVE
    )
    route = get_route(build_pn532_router(settings_service, _make_reader()), "/api/v1/pn532/probe", "POST")

    with pytest.raises(HTTPException) as exc_info:
        route.endpoint()

    assert exc_info.value.status_code == 500
    assert "Invalid effective settings" in exc_info.value.detail


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_post_pn532_probe_refuses_a_second_probe_while_one_is_running_with_409(get_route):
    nested_errors = []
    reader_builder = _make_reader()

    def build_while_probing_again(**kwargs):
        with pytest.raises(HTTPException) as exc_info:
            route.endpoint()
        nested_errors.append(exc_info.value)
        return reader_builder(**kwargs)

    route = _probe_route(get_route, build_while_probing_again)

    assert route.endpoint().firmware_version == "1.6"
    assert [(err.status_code, err.detail) for err in nested_errors] == [(409, "A probe is already running.")]
    assert route.endpoint().firmware_version == "1.6"
