from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jukebox.pn532.profiles import (
    Pn532BoardProfile,
    Pn532ConnectionParams,
    Pn532Protocol,
    SpiConnectionParams,
    resolve_connection_params,
)
from jukebox.settings.service_protocols import SettingsService
from jukebox.shared.errors import MissingOptionalDependencyError


class Pn532GpioError(RuntimeError):
    """The reader could not claim its GPIO pins: the pin configuration is likely wrong."""


@dataclass(frozen=True)
class Pn532ProbeSetup:
    board_profile: Pn532BoardProfile
    protocol: Pn532Protocol
    connection: Pn532ConnectionParams
    read_timeout_seconds: float


@dataclass(frozen=True)
class Pn532ProbeResult:
    firmware_version: tuple[int, int]
    uid: str | None


def default_build_pn532_reader(
    read_timeout_seconds: float,
    protocol: Pn532Protocol,
    connection: Pn532ConnectionParams,
) -> Any:
    from jukebox.adapters.outbound.readers.pn532_reader_adapter import Pn532ReaderAdapter

    if protocol == "spi":
        if not isinstance(connection, SpiConnectionParams):
            raise ValueError(f"Expected SpiConnectionParams for protocol 'spi', got {type(connection).__name__}")
        return Pn532ReaderAdapter(
            read_timeout_seconds=read_timeout_seconds,
            spi_reset=connection.reset,
            spi_cs=connection.cs,
            spi_irq=connection.irq,
        )
    raise ValueError(f"Unsupported PN532 protocol: {protocol}")


def resolve_pn532_probe_setup(settings_service: SettingsService) -> Pn532ProbeSetup:
    pn532 = settings_service.get_effective_settings().jukebox.reader.pn532
    overrides = SpiConnectionParams(reset=pn532.spi.reset, cs=pn532.spi.cs, irq=pn532.spi.irq)
    return Pn532ProbeSetup(
        board_profile=pn532.board_profile,
        protocol=pn532.protocol,
        connection=resolve_connection_params(pn532.board_profile, pn532.protocol, overrides),
        read_timeout_seconds=pn532.read_timeout_seconds,
    )


def probe_pn532(
    setup: Pn532ProbeSetup,
    build_pn532_reader: Callable[..., Any] = default_build_pn532_reader,
) -> Pn532ProbeResult:
    """Builds the reader, then reads its firmware version and a tag.

    Raises MissingOptionalDependencyError without the `pn532` extra, Pn532GpioError when the pins cannot be
    claimed, and RuntimeError for any other failure while building the reader."""
    try:
        reader = build_pn532_reader(
            read_timeout_seconds=setup.read_timeout_seconds,
            protocol=setup.protocol,
            connection=setup.connection,
        )
    except (MissingOptionalDependencyError, RuntimeError):
        raise
    except Exception as err:
        msg = str(err)
        if any(s in msg.lower() for s in ("not permitted", "permission", "bad gpio")):
            raise Pn532GpioError(msg) from err
        raise RuntimeError(msg) from err

    return Pn532ProbeResult(firmware_version=reader.firmware_version, uid=reader.read())
