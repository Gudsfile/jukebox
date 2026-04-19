import dataclasses
from dataclasses import dataclass
from typing import Literal, Optional

Pn532BoardProfile = Literal["waveshare_hat", "hiletgo_v3", "custom"]

Pn532Protocol = Literal["spi"]


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
    default_protocol: Pn532Protocol
    connections: dict[Pn532Protocol, Pn532ConnectionParams]


PN532_PROFILES: dict[Pn532BoardProfile, Pn532BoardProfileDefaults] = {
    "waveshare_hat": Pn532BoardProfileDefaults(
        default_protocol="spi",
        connections={"spi": SpiConnectionParams(reset=20, cs=4, irq=None)},
    ),
    "hiletgo_v3": Pn532BoardProfileDefaults(
        default_protocol="spi",
        connections={"spi": SpiConnectionParams(reset=None, cs=8, irq=None)},
    ),
    "custom": Pn532BoardProfileDefaults(
        default_protocol="spi",
        connections={"spi": SpiConnectionParams(reset=None, cs=None, irq=None)},
    ),
}


def resolve_connection_params(
    board_profile: Pn532BoardProfile,
    protocol: Pn532Protocol,
    overrides: Pn532ConnectionParams,
) -> Pn532ConnectionParams:
    """Merge per-field overrides with the profile defaults for the given protocol.

    A field value of None in *overrides* means "use the profile default".
    The custom profile has None as its own default, so None is preserved.
    """
    profile = PN532_PROFILES[board_profile]
    if protocol not in profile.connections:
        supported = list(profile.connections.keys())
        raise ValueError(
            f"Protocol '{protocol}' is not supported by board profile '{board_profile}' (supported: {supported})"
        )
    defaults = profile.connections[protocol]
    if not isinstance(overrides, type(defaults)):
        raise ValueError(
            f"Expected overrides of type {type(defaults).__name__} for protocol '{protocol}', "
            f"got {type(overrides).__name__}"
        )
    merged = {
        f.name: getattr(overrides, f.name) if getattr(overrides, f.name) is not None else getattr(defaults, f.name)
        for f in dataclasses.fields(defaults)
    }
    return type(defaults)(**merged)
