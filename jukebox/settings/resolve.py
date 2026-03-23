import copy
import os
from typing import Callable, Optional, Union

from pydantic import ValidationError

from jukebox.shared.config_utils import get_current_tag_path, get_deprecated_env_with_warning

from .dict_utils import deep_merge
from .entities import AppSettings, PlayerSettings, ResolvedAdminRuntimeConfig, ResolvedJukeboxRuntimeConfig
from .errors import InvalidSettingsError
from .repositories import SettingsRepository
from .types import JsonObject, JsonValue

_MISSING = object()


def build_environment_settings_overrides(logger_warning: Callable[[str], None]) -> JsonObject:
    overrides = {}

    library_path = get_deprecated_env_with_warning(
        "JUKEBOX_LIBRARY_PATH",
        "LIBRARY_PATH",
        None,
        logger_warning,
    )
    if library_path is not None:
        overrides.setdefault("paths", {})["library_path"] = library_path

    sonos_host = get_deprecated_env_with_warning(
        "JUKEBOX_SONOS_HOST",
        "SONOS_HOST",
        None,
        logger_warning,
    )
    if sonos_host is not None:
        overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})["manual_host"] = sonos_host

    return overrides


class SettingsReadService:
    def __init__(
        self,
        repository: SettingsRepository,
        env_overrides: Optional[JsonObject] = None,
        cli_overrides: Optional[JsonObject] = None,
    ):
        self.repository = repository
        self.env_overrides = copy.deepcopy(env_overrides or {})
        self.cli_overrides = copy.deepcopy(cli_overrides or {})

    def get_persisted_settings_view(self) -> JsonObject:
        return self.repository.load_persisted_settings_data()

    def get_effective_settings_view(self) -> JsonObject:
        effective_settings = self._resolve_effective_settings()
        effective_data = effective_settings.model_dump(mode="python")
        effective_data.pop("schema_version", None)

        return {
            "settings": effective_data,
            "provenance": _build_provenance_tree(
                effective_data,
                _without_schema_version(self.repository.load_persisted_settings_data()),
                self.env_overrides,
                self.cli_overrides,
            ),
            "derived": {
                "paths": {
                    "expanded_library_path": _expand_path(effective_settings.paths.library_path),
                    "current_tag_path": get_current_tag_path(effective_settings.paths.library_path),
                }
            },
        }

    def resolve_jukebox_runtime(self, verbose: bool = False) -> ResolvedJukeboxRuntimeConfig:
        effective_settings = self._resolve_effective_settings()
        return ResolvedJukeboxRuntimeConfig(
            library_path=_expand_path(effective_settings.paths.library_path),
            player_type=effective_settings.jukebox.player.type,
            sonos_host=_resolve_sonos_host(effective_settings.jukebox.player),
            reader_type=effective_settings.jukebox.reader.type,
            pause_duration_seconds=effective_settings.jukebox.playback.pause_duration_seconds,
            pause_delay_seconds=effective_settings.jukebox.playback.pause_delay_seconds,
            loop_interval_seconds=effective_settings.jukebox.runtime.loop_interval_seconds,
            nfc_read_timeout_seconds=effective_settings.jukebox.reader.nfc.read_timeout_seconds,
            verbose=verbose,
        )

    def resolve_admin_runtime(self, verbose: bool = False) -> ResolvedAdminRuntimeConfig:
        effective_settings = self._resolve_effective_settings()
        return ResolvedAdminRuntimeConfig(
            library_path=_expand_path(effective_settings.paths.library_path),
            api_port=effective_settings.admin.api.port,
            ui_port=effective_settings.admin.ui.port,
            verbose=verbose,
        )

    def _resolve_effective_settings(self) -> AppSettings:
        persisted_data = self.repository.load_persisted_settings_data()
        defaults_data = AppSettings().model_dump(mode="python")

        file_merged = deep_merge(defaults_data, persisted_data)
        try:
            AppSettings.model_validate(file_merged)
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid effective settings from persisted settings: {err}") from err

        env_merged = deep_merge(file_merged, self.env_overrides)
        try:
            AppSettings.model_validate(env_merged)
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid effective settings after environment overrides: {err}") from err

        cli_merged = deep_merge(env_merged, self.cli_overrides)
        try:
            effective_settings = AppSettings.model_validate(cli_merged)
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid effective settings after CLI overrides: {err}") from err

        try:
            _validate_effective_settings(effective_settings)
        except ValueError as err:
            if self.cli_overrides:
                raise InvalidSettingsError(f"Invalid effective settings after CLI overrides: {err}") from err
            if self.env_overrides:
                raise InvalidSettingsError(f"Invalid effective settings after environment overrides: {err}") from err
            raise InvalidSettingsError(f"Invalid effective settings from persisted settings: {err}") from err

        return effective_settings


def _validate_effective_settings(settings: AppSettings) -> None:
    if settings.jukebox.player.type == "sonos" and not _resolve_sonos_host(settings.jukebox.player):
        raise ValueError("jukebox.player.type='sonos' requires a valid active Sonos target after merge.")


def _resolve_sonos_host(player_settings: PlayerSettings) -> Optional[str]:
    if player_settings.sonos.selected_group is not None:
        for speaker in player_settings.sonos.selected_group.members:
            if speaker.uid == player_settings.sonos.selected_group.coordinator_uid and speaker.last_known_host:
                return speaker.last_known_host

        for speaker in player_settings.sonos.selected_group.members:
            if speaker.last_known_host:
                return speaker.last_known_host

    return player_settings.sonos.manual_host


def _build_provenance_tree(
    effective_node: JsonObject,
    file_node: JsonObject,
    env_node: JsonObject,
    cli_node: JsonObject,
) -> JsonObject:
    provenance = {}
    for key, value in effective_node.items():
        file_value = _get_child(file_node, key)
        env_value = _get_child(env_node, key)
        cli_value = _get_child(cli_node, key)

        if isinstance(value, dict):
            provenance[key] = _build_provenance_tree(
                value,
                file_value if isinstance(file_value, dict) else {},
                env_value if isinstance(env_value, dict) else {},
                cli_value if isinstance(cli_value, dict) else {},
            )
            continue

        provenance[key] = _resolve_provenance_label(file_value, env_value, cli_value)

    return provenance


def _resolve_provenance_label(file_value: object, env_value: object, cli_value: object) -> str:
    if cli_value is not _MISSING:
        return "cli"
    if env_value is not _MISSING:
        return "env"
    if file_value is not _MISSING:
        return "file"
    return "default"


def _get_child(node: JsonObject, key: str) -> Union[JsonValue, object]:
    if isinstance(node, dict) and key in node:
        return node[key]
    return _MISSING


def _expand_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def _without_schema_version(data: JsonObject) -> JsonObject:
    filtered = copy.deepcopy(data)
    filtered.pop("schema_version", None)
    return filtered
