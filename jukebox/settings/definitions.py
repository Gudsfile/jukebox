from dataclasses import dataclass
from typing import Iterable, Optional, cast

from .entities import AppSettings
from .types import JsonObject

_MISSING = object()


@dataclass(frozen=True)
class SettingChoice:
    value: str
    label: str


@dataclass(frozen=True)
class SettingSectionDefinition:
    key: str
    label: str
    description: str
    sort_order: int


@dataclass(frozen=True)
class SettingDefinition:
    path: str
    label: str
    description: str
    field_type: str
    section: str
    requires_restart: bool = False
    advanced: bool = False
    choices: tuple[SettingChoice, ...] = ()


@dataclass(frozen=True)
class EditableSettingDisplay:
    path: str
    label: str
    description: str
    field_type: str
    section: str
    section_label: str
    section_description: str
    section_sort_order: int
    requires_restart: bool
    advanced: bool
    choices: tuple[SettingChoice, ...]
    default_value: object
    persisted_value: object
    effective_value: object
    provenance: str
    is_persisted: bool
    is_pinned_default: bool


SETTING_SECTIONS = {
    "paths": SettingSectionDefinition(
        key="paths",
        label="Paths",
        description="Shared file locations used by the admin tools and jukebox runtime.",
        sort_order=0,
    ),
    "admin": SettingSectionDefinition(
        key="admin",
        label="Admin",
        description="Ports used by the admin API and admin UI processes.",
        sort_order=1,
    ),
    "playback": SettingSectionDefinition(
        key="playback",
        label="Playback",
        description="Timing controls for pause handling and the main playback loop.",
        sort_order=2,
    ),
    "player": SettingSectionDefinition(
        key="player",
        label="Player",
        description="Playback backend selection and Sonos targeting.",
        sort_order=3,
    ),
    "reader": SettingSectionDefinition(
        key="reader",
        label="Reader",
        description="Reader backend selection and NFC polling behavior.",
        sort_order=4,
    ),
}


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
    "jukebox.player.type": SettingDefinition(
        path="jukebox.player.type",
        label="Player Type",
        description="Playback backend used by jukebox playback.",
        field_type="string",
        section="player",
        requires_restart=True,
        choices=(
            SettingChoice(value="dryrun", label="Dry Run"),
            SettingChoice(value="sonos", label="Sonos"),
        ),
    ),
    "jukebox.player.sonos.selected_group": SettingDefinition(
        path="jukebox.player.sonos.selected_group",
        label="Selected Sonos Group",
        description="Durable Sonos speaker or group selection used for playback.",
        field_type="object",
        section="player",
        requires_restart=True,
    ),
    "jukebox.reader.type": SettingDefinition(
        path="jukebox.reader.type",
        label="Reader Type",
        description="Reader backend used by jukebox playback.",
        field_type="string",
        section="reader",
        requires_restart=True,
        choices=(
            SettingChoice(value="dryrun", label="Dry Run"),
            SettingChoice(value="nfc", label="NFC"),
        ),
    ),
    "jukebox.reader.nfc.read_timeout_seconds": SettingDefinition(
        path="jukebox.reader.nfc.read_timeout_seconds",
        label="NFC Read Timeout",
        description="Timeout in seconds for each NFC poll attempt.",
        field_type="number",
        section="reader",
        requires_restart=True,
    ),
}


def get_setting_definition(dotted_path: str) -> Optional[SettingDefinition]:
    return SETTINGS.get(dotted_path)


def get_setting_section_definition(section: str) -> SettingSectionDefinition:
    fallback_order = len(SETTING_SECTIONS)
    return SETTING_SECTIONS.get(
        section,
        SettingSectionDefinition(
            key=section,
            label=section.title(),
            description="",
            sort_order=fallback_order,
        ),
    )


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


def build_editable_setting_displays(
    persisted_settings: JsonObject,
    effective_settings_view: JsonObject,
) -> list[EditableSettingDisplay]:
    default_settings = AppSettings().model_dump(mode="python")
    effective_settings = _lookup_object(effective_settings_view, "settings")
    provenance = _lookup_object(effective_settings_view, "provenance")
    displays: list[EditableSettingDisplay] = []

    for dotted_path, definition in SETTINGS.items():
        section_definition = get_setting_section_definition(definition.section)
        persisted_value = _lookup_optional_dotted_path(persisted_settings, dotted_path)
        default_value = _lookup_optional_dotted_path(default_settings, dotted_path)
        effective_value = _lookup_optional_dotted_path(effective_settings, dotted_path)
        if effective_value is _MISSING:
            effective_value = persisted_value if persisted_value is not _MISSING else default_value
        displays.append(
            EditableSettingDisplay(
                path=dotted_path,
                label=definition.label,
                description=definition.description,
                field_type=definition.field_type,
                section=definition.section,
                section_label=section_definition.label,
                section_description=section_definition.description,
                section_sort_order=section_definition.sort_order,
                requires_restart=definition.requires_restart,
                advanced=definition.advanced,
                choices=definition.choices,
                default_value=_normalize_lookup_value(default_value),
                persisted_value=_normalize_lookup_value(persisted_value),
                effective_value=_normalize_lookup_value(effective_value),
                provenance=_lookup_provenance_label(provenance, dotted_path),
                is_persisted=persisted_value is not _MISSING,
                is_pinned_default=(
                    persisted_value is not _MISSING
                    and _normalize_lookup_value(persisted_value) == _normalize_lookup_value(default_value)
                ),
            )
        )

    return sorted(
        displays,
        key=lambda display: (display.section_sort_order, display.label, display.path),
    )


def build_settings_metadata_tree() -> JsonObject:
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
            "choices": [
                {
                    "value": choice.value,
                    "label": choice.label,
                }
                for choice in definition.choices
            ],
        }

    return tree


def build_change_metadata_tree() -> JsonObject:
    return build_settings_metadata_tree()


def _ensure_object_child(node: JsonObject, key: str) -> JsonObject:
    child = node.get(key)
    if not isinstance(child, dict):
        child = {}
        node[key] = child

    return cast(JsonObject, child)


def _lookup_object(node: JsonObject, key: str) -> JsonObject:
    child = node.get(key, {})
    if isinstance(child, dict):
        return child
    return {}


def _lookup_optional_dotted_path(root: JsonObject, dotted_path: str) -> object:
    current: JsonObject = root
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        child = current.get(part, _MISSING)
        if not isinstance(child, dict):
            return _MISSING
        current = cast(JsonObject, child)
    return current.get(parts[-1], _MISSING)


def _normalize_lookup_value(value: object) -> object:
    if value is _MISSING:
        return None
    return value


def _lookup_provenance_label(root: JsonObject, dotted_path: str) -> str:
    value = _lookup_optional_dotted_path(root, dotted_path)
    collapsed_label = _collapse_provenance_value(value)
    if collapsed_label is None:
        return "unknown"
    return collapsed_label


def _collapse_provenance_value(value: object) -> Optional[str]:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None

    labels = {
        label
        for child_value in value.values()
        for label in [_collapse_provenance_value(child_value)]
        if label is not None
    }
    if len(labels) == 1:
        return next(iter(labels))
    return None
