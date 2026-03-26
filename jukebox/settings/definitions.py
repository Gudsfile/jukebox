from dataclasses import dataclass
from typing import Iterable, Optional, cast

from .types import JsonObject


@dataclass(frozen=True)
class SettingDefinition:
    path: str
    label: str
    description: str
    field_type: str
    section: str
    requires_restart: bool = False
    advanced: bool = False


SETTINGS = {
    "paths.library_path": SettingDefinition(
        path="paths.library_path",
        label="Library Path",
        description="Location of the shared library JSON file.",
        field_type="string",
        section="paths",
        requires_restart=True,
    ),
    "admin.api.port": SettingDefinition(
        path="admin.api.port",
        label="Admin API Port",
        description="TCP port used by the admin API server.",
        field_type="integer",
        section="admin",
        requires_restart=True,
    ),
    "admin.ui.port": SettingDefinition(
        path="admin.ui.port",
        label="Admin UI Port",
        description="TCP port used by the admin UI server.",
        field_type="integer",
        section="admin",
        requires_restart=True,
    ),
    "jukebox.playback.pause_duration_seconds": SettingDefinition(
        path="jukebox.playback.pause_duration_seconds",
        label="Pause Duration",
        description="Maximum paused duration before playback resets.",
        field_type="integer",
        section="playback",
        requires_restart=True,
    ),
    "jukebox.playback.pause_delay_seconds": SettingDefinition(
        path="jukebox.playback.pause_delay_seconds",
        label="Pause Delay",
        description="Grace period before pausing after a tag is removed.",
        field_type="number",
        section="playback",
        requires_restart=True,
    ),
    "jukebox.runtime.loop_interval_seconds": SettingDefinition(
        path="jukebox.runtime.loop_interval_seconds",
        label="Loop Interval",
        description="Main jukebox loop pacing interval in seconds.",
        field_type="number",
        section="playback",
        requires_restart=True,
    ),
}


def get_setting_definition(dotted_path: str) -> Optional[SettingDefinition]:
    return SETTINGS.get(dotted_path)


def is_editable_setting_path(dotted_path: str) -> bool:
    return dotted_path in SETTINGS


def has_editable_setting_descendants(dotted_path: str) -> bool:
    prefix = f"{dotted_path}."
    return any(path.startswith(prefix) for path in SETTINGS)


def get_editable_paths_for_prefix(dotted_path: str) -> list[str]:
    if is_editable_setting_path(dotted_path):
        return [dotted_path]

    prefix = f"{dotted_path}."
    return sorted(path for path in SETTINGS if path.startswith(prefix))


def get_restart_required_paths(dotted_paths: Iterable[str]) -> list[str]:
    return sorted(
        dotted_path
        for dotted_path in dotted_paths
        if dotted_path in SETTINGS and SETTINGS[dotted_path].requires_restart
    )


def build_change_metadata_tree() -> JsonObject:
    tree: JsonObject = {}

    for dotted_path, definition in SETTINGS.items():
        cursor = tree
        parts = dotted_path.split(".")

        for part in parts[:-1]:
            cursor = _ensure_object_child(cursor, part)

        cursor[parts[-1]] = {
            "label": definition.label,
            "description": definition.description,
            "field_type": definition.field_type,
            "section": definition.section,
            "requires_restart": definition.requires_restart,
            "advanced": definition.advanced,
        }

    return tree


def _ensure_object_child(node: JsonObject, key: str) -> JsonObject:
    child = node.get(key)
    if not isinstance(child, dict):
        child = {}
        node[key] = child

    return cast(JsonObject, child)
