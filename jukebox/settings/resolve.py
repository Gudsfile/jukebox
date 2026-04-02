import copy
import json
import os
from typing import Callable, Optional, Tuple, Union, cast

from pydantic import ValidationError

from jukebox.shared.config_utils import get_current_tag_path, get_deprecated_env_with_warning
from jukebox.sonos.service import DefaultSonosService, SonosService

from .definitions import (
    build_settings_metadata_tree,
    get_editable_paths_for_prefix,
    get_restart_required_paths,
    get_setting_definition,
    has_editable_setting_descendants,
    is_editable_setting_path,
)
from .dict_utils import deep_merge
from .entities import (
    AppSettings,
    PersistedAppSettings,
    ResolvedAdminRuntimeConfig,
    ResolvedJukeboxRuntimeConfig,
    ResolvedSonosGroupRuntime,
)
from .errors import InvalidSettingsError
from .repositories import SettingsRepository
from .types import JsonObject, JsonValue
from .validation_rules import validate_settings_rules

_MISSING = object()
ActiveSonosTarget = Tuple[Optional[str], Optional[str], Optional[ResolvedSonosGroupRuntime]]


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
    sonos_name = os.environ.get("JUKEBOX_SONOS_NAME")
    if sonos_host is not None or sonos_name is not None:
        sonos_overrides = overrides.setdefault("jukebox", {}).setdefault("player", {}).setdefault("sonos", {})
        sonos_overrides["manual_host"] = sonos_host
        sonos_overrides["manual_name"] = sonos_name
        sonos_overrides["selected_group"] = None

    return overrides


class SettingsService:
    def __init__(
        self,
        repository: SettingsRepository,
        env_overrides: Optional[JsonObject] = None,
        cli_overrides: Optional[JsonObject] = None,
        sonos_service: Optional[SonosService] = None,
    ):
        self.repository = repository
        self.env_overrides = copy.deepcopy(env_overrides or {})
        self.cli_overrides = copy.deepcopy(cli_overrides or {})
        self.sonos_service = sonos_service

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
            "settings_metadata": build_settings_metadata_tree(),
        }

    def resolve_jukebox_runtime(self, verbose: bool = False) -> ResolvedJukeboxRuntimeConfig:
        effective_settings = self._resolve_effective_settings()
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
                _format_invalid_settings_message(str(err), self.env_overrides, self.cli_overrides)
            ) from err

    def resolve_admin_runtime(self, verbose: bool = False) -> ResolvedAdminRuntimeConfig:
        effective_settings = self._resolve_effective_settings()
        return ResolvedAdminRuntimeConfig(
            library_path=_expand_path(effective_settings.paths.library_path),
            api_port=effective_settings.admin.api.port,
            ui_port=effective_settings.admin.ui.port,
            verbose=verbose,
        )

    def set_persisted_value(self, dotted_path: str, raw_value: str) -> JsonObject:
        if not is_editable_setting_path(dotted_path):
            raise InvalidSettingsError(f"Unsupported settings path for write: '{dotted_path}'")

        current_data = self.repository.load_persisted().model_dump(mode="python")
        updated_data = copy.deepcopy(current_data)
        _set_dotted_path(updated_data, dotted_path, _parse_raw_setting_value(dotted_path, raw_value))
        return self._save_updated_settings(updated_data, [dotted_path])

    def reset_persisted_value(self, dotted_path: str) -> JsonObject:
        editable_paths = get_editable_paths_for_prefix(dotted_path)
        if not editable_paths:
            raise InvalidSettingsError(f"Unsupported settings path for reset: '{dotted_path}'")

        current_data = self.repository.load_persisted().model_dump(mode="python")
        defaults_data = PersistedAppSettings().model_dump(mode="python")
        updated_data = copy.deepcopy(current_data)
        for editable_path in editable_paths:
            _set_dotted_path(updated_data, editable_path, _get_dotted_path(defaults_data, editable_path))

        return self._save_updated_settings(updated_data, editable_paths, reset_paths=editable_paths)

    def patch_persisted_settings(self, patch: JsonObject) -> JsonObject:
        if not isinstance(patch, dict) or not patch:
            raise InvalidSettingsError("Settings patch must be a non-empty JSON object.")

        updated_paths = sorted(_collect_patch_paths(patch))
        if not updated_paths:
            raise InvalidSettingsError("Settings patch must include at least one editable field.")

        current_data = self.repository.load_persisted().model_dump(mode="python")
        updated_data = deep_merge(current_data, patch)
        return self._save_updated_settings(updated_data, updated_paths)

    def _resolve_effective_settings(self) -> AppSettings:
        # This layer only validates the merged shared settings shape. It must not
        # enforce app-specific runtime requirements for callers like discstore.
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

        return effective_settings

    def _save_updated_settings(
        self,
        updated_data: JsonObject,
        updated_paths: list[str],
        reset_paths: Optional[list[str]] = None,
    ) -> JsonObject:
        persisted_before = self.repository.load_persisted_settings_data()

        try:
            persisted_settings = PersistedAppSettings.model_validate(updated_data)
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings update: {err}") from err

        try:
            effective_settings = AppSettings.model_validate(
                deep_merge(AppSettings().model_dump(mode="python"), persisted_settings.model_dump(mode="python"))
            )
        except ValidationError as err:
            raise InvalidSettingsError(f"Invalid settings update: {err}") from err

        try:
            validate_settings_rules(effective_settings.model_dump(mode="python"), updated_paths)
        except ValueError as err:
            raise InvalidSettingsError(f"Invalid settings update: {err}") from err

        persisted_after = _build_updated_persisted_settings(
            persisted_before,
            cast(JsonObject, persisted_settings.model_dump(mode="python")),
            updated_paths,
            set(reset_paths or []),
        )
        actual_updated_paths = sorted(
            dotted_path
            for dotted_path in updated_paths
            if _get_optional_dotted_path(persisted_before, dotted_path)
            != _get_optional_dotted_path(persisted_after, dotted_path)
        )

        if not actual_updated_paths:
            return {
                "persisted": persisted_before,
                "effective": self.get_effective_settings_view(),
                "updated_paths": [],
                "restart_required": False,
                "restart_required_paths": [],
                "message": "No persisted settings changed.",
            }

        self.repository.save_persisted_settings_data(persisted_after)

        restart_required_paths = get_restart_required_paths(actual_updated_paths)
        return {
            "persisted": self.get_persisted_settings_view(),
            "effective": self.get_effective_settings_view(),
            "updated_paths": actual_updated_paths,
            "restart_required": bool(restart_required_paths),
            "restart_required_paths": restart_required_paths,
            "message": (
                "Settings saved. Changes take effect after restart." if restart_required_paths else "Settings saved."
            ),
        }

    def _resolve_active_sonos_target(self, effective_settings: AppSettings) -> ActiveSonosTarget:
        player_settings = effective_settings.jukebox.player
        if player_settings.type != "sonos":
            return None, None, None

        if player_settings.sonos.manual_host is not None:
            return player_settings.sonos.manual_host, None, None

        if player_settings.sonos.manual_name is not None:
            return None, player_settings.sonos.manual_name, None

        if player_settings.sonos.selected_group is not None:
            resolved_group = self._get_sonos_service().resolve_selected_group(player_settings.sonos.selected_group)
            return resolved_group.coordinator.host, None, resolved_group

        return None, None, None

    def _get_sonos_service(self) -> SonosService:
        if self.sonos_service is not None:
            return self.sonos_service

        from jukebox.adapters.outbound.sonos_discovery_adapter import SoCoSonosDiscoveryAdapter

        self.sonos_service = DefaultSonosService(SoCoSonosDiscoveryAdapter())
        return self.sonos_service


def _format_invalid_settings_message(error: str, env_overrides: JsonObject, cli_overrides: JsonObject) -> str:
    if cli_overrides:
        return f"Invalid effective settings after CLI overrides: {error}"
    if env_overrides:
        return f"Invalid effective settings after environment overrides: {error}"
    return f"Invalid effective settings from persisted settings: {error}"


def _expand_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


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
                cast(JsonObject, file_value) if isinstance(file_value, dict) else {},
                cast(JsonObject, env_value) if isinstance(env_value, dict) else {},
                cast(JsonObject, cli_value) if isinstance(cli_value, dict) else {},
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


def _without_schema_version(data: JsonObject) -> JsonObject:
    filtered = copy.deepcopy(data)
    filtered.pop("schema_version", None)
    return filtered


def _collect_patch_paths(node: JsonObject, prefix: Optional[str] = None) -> set[str]:
    paths = set()

    for key, value in node.items():
        dotted_path = f"{prefix}.{key}" if prefix else key

        if is_editable_setting_path(dotted_path):
            paths.add(dotted_path)
            continue

        if isinstance(value, dict):
            if not has_editable_setting_descendants(dotted_path):
                raise InvalidSettingsError(f"Unsupported settings path for write: '{dotted_path}'")
            paths.update(_collect_patch_paths(value, dotted_path))
            continue

        if not is_editable_setting_path(dotted_path):
            raise InvalidSettingsError(f"Unsupported settings path for write: '{dotted_path}'")

        paths.add(dotted_path)

    return paths


def _get_dotted_path(data: JsonObject, dotted_path: str) -> JsonValue:
    current: JsonValue = data

    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise InvalidSettingsError(f"Unknown settings path: '{dotted_path}'")
        current = current[part]

    return copy.deepcopy(current)


def _get_optional_dotted_path(data: JsonObject, dotted_path: str) -> object:
    try:
        return _get_dotted_path(data, dotted_path)
    except InvalidSettingsError:
        return _MISSING


def _build_updated_persisted_settings(
    persisted_before: JsonObject,
    validated_data: JsonObject,
    updated_paths: list[str],
    reset_paths: set[str],
) -> JsonObject:
    persisted_after = copy.deepcopy(persisted_before)

    for dotted_path in updated_paths:
        if dotted_path in reset_paths:
            _delete_dotted_path(persisted_after, dotted_path)
            continue

        _set_dotted_path(persisted_after, dotted_path, _get_dotted_path(validated_data, dotted_path))

    persisted_after["schema_version"] = validated_data["schema_version"]
    return persisted_after


def _delete_dotted_path(data: JsonObject, dotted_path: str) -> None:
    current = data
    parents = []
    parts = dotted_path.split(".")

    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            return
        parents.append((current, part, child))
        current = child

    if parts[-1] not in current:
        return

    del current[parts[-1]]

    for parent, key, child in reversed(parents):
        if child:
            break
        del parent[key]


def _set_dotted_path(data: JsonObject, dotted_path: str, value: JsonValue) -> None:
    current = data
    parts = dotted_path.split(".")

    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child

    current[parts[-1]] = copy.deepcopy(value)


def _parse_raw_setting_value(dotted_path: str, raw_value: str) -> JsonValue:
    definition = get_setting_definition(dotted_path)

    if definition is None or definition.field_type != "object":
        return raw_value

    try:
        parsed_value = json.loads(raw_value)
    except json.JSONDecodeError as err:
        raise InvalidSettingsError(f"Settings value for '{dotted_path}' must be valid JSON.") from err

    if parsed_value is not None and not isinstance(parsed_value, dict):
        raise InvalidSettingsError(f"Settings value for '{dotted_path}' must be a JSON object or null.")

    return cast(JsonValue, parsed_value)
