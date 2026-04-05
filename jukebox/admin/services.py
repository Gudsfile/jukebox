from dataclasses import dataclass

from jukebox.settings.service_protocols import SettingsService
from jukebox.sonos.service import SonosService


@dataclass(frozen=True)
class AdminServices:
    settings: SettingsService
    sonos: SonosService
