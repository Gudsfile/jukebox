from dataclasses import dataclass
from typing import Literal, Optional

Pn532BoardProfile = Literal["waveshare_hat", "hiletgo_v3", "custom"]


@dataclass(frozen=True)
class Pn532BoardProfileDefaults:
    reset: Optional[int]
    cs: Optional[int]
    irq: Optional[int]


PN532_PROFILES: dict[Pn532BoardProfile, Pn532BoardProfileDefaults] = {
    "waveshare_hat": Pn532BoardProfileDefaults(reset=20, cs=4, irq=None),
    "hiletgo_v3": Pn532BoardProfileDefaults(reset=None, cs=8, irq=None),
    "custom": Pn532BoardProfileDefaults(reset=None, cs=None, irq=None),
}


def resolve_spi_pins(
    board_profile: Pn532BoardProfile,
    reset: Optional[int],
    cs: Optional[int],
    irq: Optional[int],
) -> Pn532BoardProfileDefaults:
    profile = PN532_PROFILES[board_profile]
    return Pn532BoardProfileDefaults(
        reset=reset if reset is not None else profile.reset,
        cs=cs if cs is not None else profile.cs,
        irq=irq if irq is not None else profile.irq,
    )
