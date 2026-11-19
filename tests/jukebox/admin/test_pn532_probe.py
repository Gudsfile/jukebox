from unittest.mock import MagicMock

import pytest

from jukebox.admin.pn532_probe import (
    Pn532GpioError,
    Pn532ProbeResult,
    Pn532ProbeSetup,
    probe_pn532,
    resolve_pn532_probe_setup,
)
from jukebox.pn532.profiles import SpiConnectionParams
from jukebox.settings.entities import AppSettings
from jukebox.shared.errors import MissingOptionalDependencyError

SETUP = Pn532ProbeSetup(
    board_profile="waveshare_hat",
    protocol="spi",
    connection=SpiConnectionParams(reset=20, cs=4, irq=None),
    read_timeout_seconds=0.1,
)


def _make_reader(firmware_version=(1, 6), uid=None):
    mock_reader = MagicMock()
    mock_reader.firmware_version = firmware_version
    mock_reader.read.return_value = uid
    return MagicMock(return_value=mock_reader)


def _failing_builder(error: Exception):
    def build(**_kwargs):
        raise error

    return build


def test_resolve_pn532_probe_setup_merges_profile_defaults_with_overrides():
    service = MagicMock()
    service.get_effective_settings.return_value = AppSettings.model_validate(
        {"jukebox": {"reader": {"pn532": {"board_profile": "waveshare_hat", "spi": {"cs": 8}}}}}
    )

    setup = resolve_pn532_probe_setup(service)

    assert setup.board_profile == "waveshare_hat"
    assert setup.protocol == "spi"
    assert setup.connection == SpiConnectionParams(reset=20, cs=8, irq=None)


def test_probe_pn532_returns_firmware_version_and_uid():
    build_fn = _make_reader(firmware_version=(1, 6), uid="04:ab:cd:ef")

    result = probe_pn532(SETUP, build_fn)

    assert result == Pn532ProbeResult(firmware_version=(1, 6), uid="04:ab:cd:ef")
    build_fn.assert_called_once_with(read_timeout_seconds=0.1, protocol="spi", connection=SETUP.connection)


def test_probe_pn532_returns_no_uid_without_tag():
    assert probe_pn532(SETUP, _make_reader(uid=None)).uid is None


def test_probe_pn532_propagates_missing_extra():
    error = MissingOptionalDependencyError("subject", "pn532", "run_command")

    with pytest.raises(MissingOptionalDependencyError) as exc_info:
        probe_pn532(SETUP, _failing_builder(error))

    assert exc_info.value is error


def test_probe_pn532_propagates_runtime_errors_unchanged():
    error = RuntimeError("SPI interface not enabled. Use raspi-config to enable it.")

    with pytest.raises(RuntimeError) as exc_info:
        probe_pn532(SETUP, _failing_builder(error))

    assert exc_info.value is error


@pytest.mark.parametrize("raw_error", ["GPIO operation not permitted", "bad GPIO number", "Permission denied"])
def test_probe_pn532_maps_gpio_errors(raw_error):
    with pytest.raises(Pn532GpioError, match=raw_error):
        probe_pn532(SETUP, _failing_builder(OSError(raw_error)))


def test_probe_pn532_wraps_other_errors_in_runtime_error():
    with pytest.raises(RuntimeError, match="boom") as exc_info:
        probe_pn532(SETUP, _failing_builder(ValueError("boom")))

    assert not isinstance(exc_info.value, Pn532GpioError)
