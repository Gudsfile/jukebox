import dataclasses
from dataclasses import dataclass
from typing import Literal, Optional

Pn532BoardProfile = Literal["waveshare_hat", "hiletgo_v3", "custom"]


@dataclass(frozen=True)
class SpiConnectionParams:
    reset: Optional[int]
    cs: Optional[int]
    irq: Optional[int]


# Today SpiConnectionParams only; Union[SpiConnectionParams, UartConnectionParams, ...]
# will be introduced when additional protocols are added.
Pn532ConnectionParams = SpiConnectionParams


@dataclass(frozen=True)
class Pn532BoardProfileDefaults:
    protocol: Literal["spi"]
    connection: Pn532ConnectionParams


PN532_PROFILES: dict[Pn532BoardProfile, Pn532BoardProfileDefaults] = {
    "waveshare_hat": Pn532BoardProfileDefaults(
        protocol="spi",
        connection=SpiConnectionParams(reset=20, cs=4, irq=None),
    ),
    "hiletgo_v3": Pn532BoardProfileDefaults(
        protocol="spi",
        connection=SpiConnectionParams(reset=None, cs=8, irq=None),
    ),
    "custom": Pn532BoardProfileDefaults(
        protocol="spi",
        connection=SpiConnectionParams(reset=None, cs=None, irq=None),
    ),
}


def resolve_connection_params(
    board_profile: Pn532BoardProfile,
    overrides: Pn532ConnectionParams,
) -> Pn532ConnectionParams:
    """Merge per-field overrides with the profile defaults.

    A field value of None in *overrides* means "use the profile default".
    The custom profile has None as its own default, so None is preserved.
    """
    defaults = PN532_PROFILES[board_profile].connection
    merged = {
        f.name: getattr(overrides, f.name) if getattr(overrides, f.name) is not None else getattr(defaults, f.name)
        for f in dataclasses.fields(defaults)
    }
    return type(defaults)(**merged)
