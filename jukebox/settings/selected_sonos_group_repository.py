from typing import Optional

from jukebox.sonos.selection import (
    SaveSelectedSonosGroupResult,
    SelectedSonosGroupRepository,
)

from .entities import SelectedSonosGroupSettings
from .service_protocols import SettingsService
from .types import JsonObject


class SettingsSelectedSonosGroupRepository(SelectedSonosGroupRepository):
    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service

    def get_selected_group(self) -> Optional[SelectedSonosGroupSettings]:
        persisted = self.settings_service.get_persisted_settings_view()
        selected_group_data = _lookup_selected_group(persisted)
        if selected_group_data is None:
            return None
        return SelectedSonosGroupSettings.model_validate(selected_group_data)

    def save_selected_group(self, selected_group: SelectedSonosGroupSettings) -> SaveSelectedSonosGroupResult:
        settings_result = self.settings_service.patch_persisted_settings(
            {
                "jukebox": {
                    "player": {
                        "type": "sonos",
                        "sonos": {
                            "selected_group": selected_group.model_dump(mode="python"),
                        },
                    }
                }
            }
        )
        return SaveSelectedSonosGroupResult(
            message=str(settings_result.get("message", "Settings saved.")),
            restart_required=bool(settings_result.get("restart_required", False)),
        )


def _lookup_selected_group(persisted: JsonObject) -> Optional[JsonObject]:
    jukebox_settings = persisted.get("jukebox")
    if not isinstance(jukebox_settings, dict):
        return None

    player_settings = jukebox_settings.get("player")
    if not isinstance(player_settings, dict):
        return None

    sonos_settings = player_settings.get("sonos")
    if not isinstance(sonos_settings, dict):
        return None

    selected_group = sonos_settings.get("selected_group")
    if not isinstance(selected_group, dict):
        return None

    return selected_group
