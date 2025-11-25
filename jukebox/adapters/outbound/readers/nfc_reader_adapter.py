from __future__ import annotations

import logging
import os
from typing import Union

try:
    from pn532 import PN532_SPI
except ModuleNotFoundError as err:
    raise ModuleNotFoundError("The `nfc reader` requires `pip install gukebox[nfc]`.") from err

from jukebox.domain.ports import ReaderPort

LOGGER = logging.getLogger("jukebox")


def parse_raw_uid(raw: bytearray):
    return ":".join([hex(i)[2:].lower().rjust(2, "0") for i in raw])


def spi_active():
    return any(dev.startswith("spidev") for dev in os.listdir("/dev"))


class NfcReaderAdapter(ReaderPort):
    """Adapter for NFC reader implementing ReaderPort."""

    def __init__(self):
        if not spi_active():
            error_message = (
                "The SPI interface is not enabled. Please enable it to use the NFC reader."
                "You can enable SPI using `sudo raspi-config` then navigate to: Interface Options > SPI > Enable > Yes."
            )
            LOGGER.error(error_message)
            raise RuntimeError("SPI interface not enabled. Use raspi-config to enable it.")

        self.pn532 = PN532_SPI(debug=False, reset=20, cs=4)
        ic, ver, rev, support = self.pn532.get_firmware_version()
        LOGGER.info(f"Found PN532 with firmware version: {ver}.{rev}")
        self.pn532.SAM_configuration()

    def read(self) -> Union[str, None]:
        rawuid = self.pn532.read_passive_target(timeout=0.5)
        if rawuid is None:
            return None
        return parse_raw_uid(rawuid)
