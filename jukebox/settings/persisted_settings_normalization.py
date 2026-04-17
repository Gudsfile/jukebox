import copy
from typing import Optional

from .types import JsonObject


def normalize_persisted_settings_data(data: JsonObject) -> JsonObject:
    normalized = copy.deepcopy(data)
    selected_group = _lookup_selected_group(normalized)
    if selected_group is not None:
        selected_group.pop("household_id", None)
    return normalized


def _lookup_selected_group(data: JsonObject) -> Optional[JsonObject]:
    jukebox_settings = data.get("jukebox")
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
