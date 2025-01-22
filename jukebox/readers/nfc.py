from __future__ import annotations

from pn532 import PN532_SPI

from .reader import Reader


def parse_raw_uid(raw: bytearray):
    return ":".join([hex(i)[2:].lower().rjust(2, "0") for i in raw])


class NFCReader(Reader):
    def __init__(self):
        self.pn532 = PN532_SPI(debug=False, reset=20, cs=4)
        ic, ver, rev, support = self.pn532.get_firmware_version()
        print(f"Found PN532 with firmware version: {ver}.{rev}")
        self.pn532.SAM_configuration()

    def read(self) -> str:
        rawuid = self.pn532.read_passive_target(timeout=0.5)
        if rawuid is None:
            return None
        return parse_raw_uid(rawuid)
