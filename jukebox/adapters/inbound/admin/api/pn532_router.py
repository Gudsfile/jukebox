from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jukebox.pn532.profiles import PN532_PROFILES, SpiConnectionParams, resolve_connection_params
from jukebox.settings.definitions import get_setting_definition
from jukebox.settings.service_protocols import SettingsService


class Pn532PinsOutput(BaseModel):
    reset: int | None
    cs: int | None
    irq: int | None


class Pn532ProfileOutput(BaseModel):
    name: str
    label: str
    protocol: str
    defaults: Pn532PinsOutput


class Pn532ConfigOutput(BaseModel):
    board_profile: str
    protocol: str
    overrides: Pn532PinsOutput
    resolved: Pn532PinsOutput
    profiles: list[Pn532ProfileOutput]


def _pins(params: SpiConnectionParams) -> Pn532PinsOutput:
    return Pn532PinsOutput(reset=params.reset, cs=params.cs, irq=params.irq)


def _profile_labels() -> dict[str, str]:
    definition = get_setting_definition("jukebox.reader.pn532.board_profile")
    return {choice.value: choice.label for choice in definition.choices} if definition else {}


def build_pn532_router(settings_service: SettingsService) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["pn532"])

    @router.get(
        "/pn532",
        response_model=Pn532ConfigOutput,
        summary="Get the effective PN532 config (profile defaults merged with pin overrides)",
    )
    def get_pn532() -> Pn532ConfigOutput:
        try:
            pn532 = settings_service.get_effective_settings().jukebox.reader.pn532
            overrides = SpiConnectionParams(reset=pn532.spi.reset, cs=pn532.spi.cs, irq=pn532.spi.irq)
            resolved = resolve_connection_params(pn532.board_profile, pn532.protocol, overrides)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {err!s}")

        labels = _profile_labels()
        return Pn532ConfigOutput(
            board_profile=pn532.board_profile,
            protocol=pn532.protocol,
            overrides=_pins(overrides),
            resolved=_pins(resolved),
            profiles=[
                Pn532ProfileOutput(
                    name=name,
                    label=labels.get(name, name),
                    protocol=profile.default_protocol,
                    defaults=_pins(profile.connections[profile.default_protocol]),
                )
                for name, profile in PN532_PROFILES.items()
            ],
        )

    return router
