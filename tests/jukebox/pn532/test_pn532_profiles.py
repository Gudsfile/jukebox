import pytest

from jukebox.pn532.profiles import PN532_PROFILES, resolve_spi_pins


def test_waveshare_hat_profile_defaults():
    profile = PN532_PROFILES["waveshare_hat"]
    assert profile.reset == 20
    assert profile.cs == 4
    assert profile.irq is None


def test_hiletgo_v3_profile_defaults():
    profile = PN532_PROFILES["hiletgo_v3"]
    assert profile.reset is None
    assert profile.cs == 8
    assert profile.irq is None


def test_custom_profile_has_no_defaults():
    profile = PN532_PROFILES["custom"]
    assert profile.reset is None
    assert profile.cs is None
    assert profile.irq is None


@pytest.mark.parametrize("profile_name", ["waveshare_hat", "hiletgo_v3", "custom"])
def test_all_profiles_are_defined(profile_name):
    assert profile_name in PN532_PROFILES


def test_resolve_spi_pins_uses_profile_defaults_when_no_overrides():
    resolved = resolve_spi_pins("waveshare_hat", reset=None, cs=None, irq=None)
    assert resolved.reset == 20
    assert resolved.cs == 4
    assert resolved.irq is None


def test_resolve_spi_pins_partial_override_wins_over_profile_default():
    resolved = resolve_spi_pins("waveshare_hat", reset=24, cs=None, irq=None)
    assert resolved.reset == 24  # override
    assert resolved.cs == 4  # profile default


def test_resolve_spi_pins_full_override_ignores_profile():
    resolved = resolve_spi_pins("waveshare_hat", reset=24, cs=10, irq=25)
    assert resolved.reset == 24
    assert resolved.cs == 10
    assert resolved.irq == 25


def test_resolve_spi_pins_none_override_is_treated_as_no_override():
    # None means "no override, use profile default", it does not force the pin to None.
    resolved = resolve_spi_pins("waveshare_hat", reset=None, cs=None, irq=None)
    assert resolved.reset == 20  # profile default, not None


def test_resolve_spi_pins_custom_profile_preserves_none_pins():
    # Use the custom profile to explicitly keep a pin as None.
    resolved = resolve_spi_pins("custom", reset=None, cs=None, irq=None)
    assert resolved.reset is None
    assert resolved.cs is None
    assert resolved.irq is None
