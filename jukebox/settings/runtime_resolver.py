from typing import Optional, Tuple

from pydantic import ValidationError

from jukebox.sonos.service import SonosService

from .entities import AppSettings, ResolvedJukeboxRuntimeConfig, ResolvedSonosGroupRuntime
from .errors import InvalidSettingsError
from .resolve import SettingsService, _expand_path, _format_invalid_settings_message
from .validation_rules import validate_settings_rules

ActiveSonosTarget = Tuple[Optional[str], Optional[str], Optional[ResolvedSonosGroupRuntime]]


class JukeboxRuntimeResolver:
    def __init__(self, settings_service: SettingsService, sonos_service: SonosService):
        self.settings_service = settings_service
        self.sonos_service = sonos_service

    def resolve(self, verbose: bool = False) -> ResolvedJukeboxRuntimeConfig:
        effective_settings = self.settings_service.get_effective_settings()
        try:
            validate_settings_rules(effective_settings.model_dump(mode="python"))
            sonos_host, sonos_name, sonos_group = self._resolve_active_sonos_target(effective_settings)
            # Runtime-only invariants belong on the resolved runtime config so
            # admin/settings inspection can still work with incomplete jukebox settings.
            return ResolvedJukeboxRuntimeConfig(
                library_path=_expand_path(effective_settings.paths.library_path),
                player_type=effective_settings.jukebox.player.type,
                sonos_host=sonos_host,
                sonos_name=sonos_name,
                sonos_group=sonos_group,
                reader_type=effective_settings.jukebox.reader.type,
                pause_duration_seconds=effective_settings.jukebox.playback.pause_duration_seconds,
                pause_delay_seconds=effective_settings.jukebox.playback.pause_delay_seconds,
                loop_interval_seconds=effective_settings.jukebox.runtime.loop_interval_seconds,
                nfc_read_timeout_seconds=effective_settings.jukebox.reader.nfc.read_timeout_seconds,
                verbose=verbose,
            )
        except (ValidationError, ValueError) as err:
            raise InvalidSettingsError(
                _format_invalid_settings_message(
                    str(err),
                    self.settings_service.env_overrides,
                    self.settings_service.cli_overrides,
                )
            ) from err

    def _resolve_active_sonos_target(self, effective_settings: AppSettings) -> ActiveSonosTarget:
        player_settings = effective_settings.jukebox.player
        if player_settings.type != "sonos":
            return None, None, None

        if player_settings.sonos.manual_host is not None:
            return player_settings.sonos.manual_host, None, None

        if player_settings.sonos.manual_name is not None:
            return None, player_settings.sonos.manual_name, None

        if player_settings.sonos.selected_group is not None:
            resolved_group = self.sonos_service.resolve_selected_group(player_settings.sonos.selected_group)
            return resolved_group.coordinator.host, None, resolved_group

        return None, None, None
