import os
from typing import Optional

from .entities import AppSettings, PlayerSettings, ResolvedAdminRuntimeConfig, ResolvedJukeboxRuntimeConfig


def expand_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def build_resolved_jukebox_runtime_config(
    settings: AppSettings,
    verbose: bool = False,
) -> ResolvedJukeboxRuntimeConfig:
    return ResolvedJukeboxRuntimeConfig(
        library_path=expand_path(settings.paths.library_path),
        player_type=settings.jukebox.player.type,
        sonos_host=resolve_sonos_host(settings.jukebox.player),
        sonos_name=resolve_sonos_name(settings.jukebox.player),
        reader_type=settings.jukebox.reader.type,
        pause_duration_seconds=settings.jukebox.playback.pause_duration_seconds,
        pause_delay_seconds=settings.jukebox.playback.pause_delay_seconds,
        loop_interval_seconds=settings.jukebox.runtime.loop_interval_seconds,
        nfc_read_timeout_seconds=settings.jukebox.reader.nfc.read_timeout_seconds,
        verbose=verbose,
    )


def build_resolved_admin_runtime_config(
    settings: AppSettings,
    verbose: bool = False,
) -> ResolvedAdminRuntimeConfig:
    return ResolvedAdminRuntimeConfig(
        library_path=expand_path(settings.paths.library_path),
        api_port=settings.admin.api.port,
        ui_port=settings.admin.ui.port,
        verbose=verbose,
    )


def resolve_sonos_host(player_settings: PlayerSettings) -> Optional[str]:
    if player_settings.sonos.manual_host is not None:
        return player_settings.sonos.manual_host

    if player_settings.sonos.manual_name is not None:
        return None

    if player_settings.sonos.selected_group is not None:
        for speaker in player_settings.sonos.selected_group.members:
            if speaker.uid == player_settings.sonos.selected_group.coordinator_uid and speaker.last_known_host:
                return speaker.last_known_host

        for speaker in player_settings.sonos.selected_group.members:
            if speaker.last_known_host:
                return speaker.last_known_host

    return None


def resolve_sonos_name(player_settings: PlayerSettings) -> Optional[str]:
    if player_settings.sonos.manual_name is not None:
        return player_settings.sonos.manual_name

    if resolve_sonos_host(player_settings) is not None:
        return None

    return None
