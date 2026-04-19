from dataclasses import dataclass
from typing import Optional

import pytest

from jukebox.pn532.profiles import PN532_PROFILES, SpiConnectionParams, resolve_connection_params


def test_waveshare_hat_profile_defaults():
    profile = PN532_PROFILES["waveshare_hat"]
    assert profile.default_protocol == "spi"
    conn = profile.connections.get("spi")
    assert isinstance(conn, SpiConnectionParams)
    assert conn.reset == 20
    assert conn.cs == 4
    assert conn.irq is None


def test_hiletgo_v3_profile_defaults():
    profile = PN532_PROFILES["hiletgo_v3"]
    assert profile.default_protocol == "spi"
    conn = profile.connections.get("spi")
    assert isinstance(conn, SpiConnectionParams)
    assert conn.reset is None
    assert conn.cs == 8
    assert conn.irq is None


def test_custom_profile_has_no_defaults():
    profile = PN532_PROFILES["custom"]
    assert profile.default_protocol == "spi"
    conn = profile.connections.get("spi")
    assert isinstance(conn, SpiConnectionParams)
    assert conn.reset is None
    assert conn.cs is None
    assert conn.irq is None


@pytest.mark.parametrize("profile_name", ["waveshare_hat", "hiletgo_v3", "custom"])
def test_all_profiles_are_defined(profile_name):
    assert profile_name in PN532_PROFILES


def test_resolve_connection_params_uses_profile_defaults_when_overrides_are_none():
    resolved = resolve_connection_params("waveshare_hat", "spi", SpiConnectionParams(reset=None, cs=None, irq=None))
    assert isinstance(resolved, SpiConnectionParams)
    assert resolved.reset == 20
    assert resolved.cs == 4
    assert resolved.irq is None


def test_resolve_connection_params_override_wins_over_default():
    resolved = resolve_connection_params("waveshare_hat", "spi", SpiConnectionParams(reset=24, cs=None, irq=None))
    assert resolved.reset == 24
    assert resolved.cs == 4  # profile default


def test_resolve_connection_params_full_override_ignores_profile():
    resolved = resolve_connection_params("waveshare_hat", "spi", SpiConnectionParams(reset=24, cs=10, irq=25))
    assert resolved.reset == 24
    assert resolved.cs == 10
    assert resolved.irq == 25


def test_resolve_connection_params_none_override_is_treated_as_no_override():
    # None means "no override, use profile default", it does not force the pin to None.
    resolved = resolve_connection_params("waveshare_hat", "spi", SpiConnectionParams(reset=None, cs=None, irq=None))
    assert resolved.reset == 20  # profile default, not None


def test_resolve_connection_params_custom_profile_preserves_none_pins():
    # Use the custom profile to explicitly keep a pin as None.
    resolved = resolve_connection_params("custom", "spi", SpiConnectionParams(reset=None, cs=None, irq=None))
    assert resolved.reset is None
    assert resolved.cs is None
    assert resolved.irq is None


def test_resolve_connection_params_raises_for_unsupported_protocol():
    with pytest.raises(ValueError, match="not supported by board profile"):
        resolve_connection_params(
            "waveshare_hat",
            "unsupported",  # ty: ignore[invalid-argument-type]
            SpiConnectionParams(reset=None, cs=None, irq=None),
        )


def test_resolve_connection_params_raises_for_mismatched_override_type():
    @dataclass(frozen=True)
    class UartConnectionParams:
        tx: Optional[int]
        rx: Optional[int]

    with pytest.raises(ValueError, match="Expected overrides of type SpiConnectionParams"):
        resolve_connection_params(
            "waveshare_hat",
            "spi",
            UartConnectionParams(tx=None, rx=None),  # ty: ignore[invalid-argument-type]
        )
