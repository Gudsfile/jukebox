from typing import Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel, ConfigDict

from jukebox.settings.entities import (
    SelectedSonosGroupSettings,
    SelectedSonosSpeakerSettings,
)
from jukebox.settings.service_protocols import ReadOnlySettingsService, SettingsService
from jukebox.settings.types import JsonObject

from .discovery import DiscoveredSonosSpeaker
from .service import SonosService


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SonosSelectionAvailability(StrictModel):
    status: Literal["not_selected", "available", "unavailable"]
    speaker: Optional[DiscoveredSonosSpeaker] = None


class SonosSelectionStatus(StrictModel):
    selected_group: Optional[SelectedSonosGroupSettings] = None
    availability: SonosSelectionAvailability

    @property
    def selected_uid(self) -> Optional[str]:
        if self.selected_group is None:
            return None
        return self.selected_group.coordinator_uid


class SonosSelectionResult(StrictModel):
    speaker: DiscoveredSonosSpeaker
    selected_group: SelectedSonosGroupSettings
    settings_message: str
    restart_required: bool = False


class SelectDefaultSonosSpeaker:
    def __init__(self, settings_service: SettingsService, sonos_service: SonosService):
        self.settings_service = settings_service
        self.sonos_service = sonos_service

    def execute(self, uid: str) -> SonosSelectionResult:
        speakers_by_uid = {speaker.uid: speaker for speaker in self.sonos_service.list_available_speakers()}
        speaker = speakers_by_uid.get(uid)
        if speaker is None:
            raise ValueError("Selected Sonos speaker is not currently discoverable: {}".format(uid))

        selected_group = SelectedSonosGroupSettings(
            coordinator_uid=uid,
            members=[SelectedSonosSpeakerSettings(uid=uid)],
        )
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
        return SonosSelectionResult(
            speaker=speaker,
            selected_group=selected_group,
            settings_message=str(settings_result.get("message", "Settings saved.")),
            restart_required=bool(settings_result.get("restart_required", False)),
        )


class GetSonosSelectionStatus:
    def __init__(self, settings_service: ReadOnlySettingsService, sonos_service: SonosService):
        self.settings_service = settings_service
        self.sonos_service = sonos_service

    def execute(self) -> SonosSelectionStatus:
        persisted = self.settings_service.get_persisted_settings_view()
        selected_group_data = _lookup_selected_group(persisted)
        if selected_group_data is None:
            return SonosSelectionStatus(
                selected_group=None,
                availability=SonosSelectionAvailability(status="not_selected", speaker=None),
            )

        selected_group = SelectedSonosGroupSettings.model_validate(selected_group_data)
        available_speakers = {speaker.uid: speaker for speaker in self.sonos_service.list_available_speakers()}
        selected_speaker = available_speakers.get(selected_group.coordinator_uid)
        if selected_speaker is None:
            availability = SonosSelectionAvailability(status="unavailable", speaker=None)
        else:
            availability = SonosSelectionAvailability(status="available", speaker=selected_speaker)

        return SonosSelectionStatus(
            selected_group=selected_group,
            availability=availability,
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
