import json
import re
import shlex
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, cast

from jukebox.settings.definitions import SETTINGS, get_setting_definition, is_editable_setting_path
from jukebox.settings.errors import (
    InvalidSettingsError,
    MalformedSettingsFileError,
    SettingsError,
    UnsupportedSettingsVersionError,
)
from jukebox.settings.types import JsonObject, JsonValue
from jukebox.settings.view_utils import MISSING, lookup_object, lookup_optional_dotted_path, lookup_provenance_label
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import SonosSelectionResult, SonosSelectionStatus

from .commands import SettingsResetCommand, SettingsSetCommand, SettingsShowCommand

_SECTION_ORDER = ("paths", "admin", "playback", "reader", "player", "other")
_VALIDATION_SUFFIX_RE = re.compile(r"\s+\[type=.*$")


def render_settings_output(
    command: object,
    payload: Mapping[str, object],
) -> str:
    if isinstance(command, SettingsShowCommand):
        if command.json_output:
            return json.dumps(payload, indent=2)
        settings_payload = cast(JsonObject, payload)
        if command.effective:
            return _render_effective_settings(settings_payload)
        return _render_persisted_settings(settings_payload)

    if isinstance(command, (SettingsSetCommand, SettingsResetCommand)):
        if command.json_output:
            return json.dumps(payload, indent=2)
        return _render_write_result(cast(JsonObject, payload))

    raise TypeError("Unsupported settings command")


def build_discstore_settings_deprecation_warning(command: object, library: Optional[str] = None) -> str:
    return (
        "Warning: `discstore settings ...` is deprecated and will be removed in a future release. "
        "Use {} instead.".format(_build_equivalent_jukebox_admin_command(command, library=library))
    )


def render_cli_error(err: BaseException, verbose: bool = False) -> str:
    message = _render_cli_error_message(err)
    if verbose and str(err) and str(err) != message:
        return "{}\n\nDetails: {}".format(message, str(err))
    return message


def render_sonos_speakers_output(speakers: list[DiscoveredSonosSpeaker]) -> str:
    if not speakers:
        return "No visible Sonos speakers found."

    name_width = max(len(speaker.name) for speaker in speakers)
    host_width = max(len(speaker.host) for speaker in speakers)
    return "\n".join(
        "{index}. {name:<{name_width}}   {host:<{host_width}}   {uid}".format(
            index=index,
            name=speaker.name,
            name_width=name_width,
            host=speaker.host,
            host_width=host_width,
            uid=speaker.uid,
        )
        for index, speaker in enumerate(speakers, start=1)
    )


def build_sonos_speaker_choice_label(speaker: DiscoveredSonosSpeaker) -> str:
    return "{} ({})".format(speaker.name, speaker.host)


def render_sonos_selection_saved_output(result: SonosSelectionResult) -> str:
    member_labels = ", ".join("{} [{}]".format(member.name, member.uid) for member in result.members)
    return "\n".join(
        [
            "Selected Sonos group saved.",
            "Coordinator: {} [{}]".format(result.coordinator.name, result.coordinator.uid),
            "Members: {}".format(member_labels),
            result.settings_message,
        ]
    )


def render_sonos_selection_status_output(status: SonosSelectionStatus) -> str:
    lines = ["Selected Sonos Group", ""]

    if status.selected_group is None:
        lines.append("- Status: not selected")
        return "\n".join(lines)

    status_label = "partially available" if status.availability.status == "partial" else status.availability.status
    coordinator_speaker = next(
        (
            member.speaker
            for member in status.availability.members
            if member.uid == status.selected_group.coordinator_uid and member.speaker is not None
        ),
        None,
    )
    if coordinator_speaker is None:
        lines.append("- Coordinator UID: {}".format(status.selected_group.coordinator_uid))
    else:
        lines.append("- Coordinator: {} [{}]".format(coordinator_speaker.name, coordinator_speaker.uid))
    lines.append("- Status: {}".format(status_label))
    lines.append("- Members:")

    name_width = max(
        len(member.speaker.name) if member.speaker is not None else len("unavailable")
        for member in status.availability.members
    )
    host_width = max(
        len(member.speaker.host) if member.speaker is not None else len("-") for member in status.availability.members
    )
    household_width = max(
        len(member.speaker.household_id) if member.speaker is not None else len("-")
        for member in status.availability.members
    )

    for member in status.availability.members:
        speaker = member.speaker
        lines.append(
            "  - {uid:<18}  {name:<{name_width}}  {host:<{host_width}}  {household:<{household_width}}  {status}".format(
                uid=member.uid,
                name=speaker.name if speaker is not None else "unavailable",
                name_width=name_width,
                host=speaker.host if speaker is not None else "-",
                host_width=host_width,
                household=speaker.household_id if speaker is not None else "-",
                household_width=household_width,
                status=member.status,
            )
        )

    return "\n".join(lines)


def _render_persisted_settings(payload: JsonObject) -> str:
    lines = ["Persisted Settings", "Schema Version: {}".format(payload.get("schema_version", "unknown"))]
    entries = list(_collect_persisted_entries(payload))

    if not entries:
        lines.append("")
        lines.append("No persisted overrides.")
        return "\n".join(lines)

    grouped_entries = _group_entries_by_section(entries)
    for section in _SECTION_ORDER:
        section_entries = grouped_entries.get(section, [])
        if not section_entries:
            continue
        lines.append("")
        lines.append(_format_section_title(section))
        for dotted_path, value in section_entries:
            lines.append("- {}: {}".format(_format_entry_label(dotted_path), _format_value(dotted_path, value)))

    return "\n".join(lines)


def _render_effective_settings(payload: JsonObject) -> str:
    settings = lookup_object(payload, "settings")
    provenance = lookup_object(payload, "provenance")
    derived = lookup_object(payload, "derived")
    grouped_entries = _group_entries_by_section(_collect_leaf_entries(settings))

    lines = ["Effective Settings"]

    for section in _SECTION_ORDER:
        definitions = [definition for definition in SETTINGS.values() if definition.section == section]
        section_entries = grouped_entries.get(section, [])
        if not definitions and not section_entries:
            continue

        lines.append("")
        lines.append(_format_section_title(section))
        rendered_paths = set()
        for definition in definitions:
            value = lookup_optional_dotted_path(settings, definition.path)
            if value is MISSING:
                value = None
            provenance_label = lookup_provenance_label(provenance, definition.path)
            lines.append(
                "- {}: {}{}".format(
                    _format_entry_label(definition.path),
                    _format_value(definition.path, value),
                    _format_effective_suffix(
                        provenance_label,
                        definition.requires_restart,
                    ),
                )
            )
            rendered_paths.add(definition.path)

        for dotted_path, value in section_entries:
            if dotted_path in rendered_paths:
                continue

            definition = get_setting_definition(dotted_path)
            provenance_label = lookup_provenance_label(provenance, dotted_path)
            lines.append(
                "- {}: {}{}".format(
                    _format_entry_label(dotted_path),
                    _format_value(dotted_path, value),
                    _format_effective_suffix(
                        provenance_label,
                        definition.requires_restart if definition is not None else False,
                    ),
                )
            )

    derived_entries = list(_collect_generic_entries(derived, prefix="derived"))
    if derived_entries:
        lines.append("")
        lines.append("Derived")
        for dotted_path, value in derived_entries:
            lines.append("- {}: {}".format(_format_entry_label(dotted_path), _format_value(dotted_path, value)))

    return "\n".join(lines)


def _render_write_result(payload: JsonObject) -> str:
    updated_paths = payload.get("updated_paths", [])
    restart_required = bool(payload.get("restart_required"))
    restart_required_paths = payload.get("restart_required_paths", [])
    message = payload.get("message", "Settings command completed.")

    lines = [str(message)]

    if isinstance(updated_paths, list) and updated_paths:
        lines.append("")
        lines.append("Changed Paths")
        for dotted_path in updated_paths:
            if isinstance(dotted_path, str):
                lines.append("- {}".format(_format_entry_label(dotted_path)))

    lines.append("")
    lines.append("Restart Required: {}".format("yes" if restart_required else "no"))

    if isinstance(restart_required_paths, list) and restart_required_paths:
        lines.append("")
        lines.append("Restart-Required Paths")
        for dotted_path in restart_required_paths:
            if isinstance(dotted_path, str):
                lines.append("- {}".format(_format_entry_label(dotted_path)))

    return "\n".join(lines)


def _format_effective_suffix(provenance: str, requires_restart: bool) -> str:
    suffix_parts = ["source: {}".format(provenance)]
    if requires_restart:
        suffix_parts.append("restart required")
    return " ({})".format("; ".join(suffix_parts))


def _collect_persisted_entries(node: JsonObject, prefix: Optional[str] = None) -> Iterable[Tuple[str, JsonValue]]:
    for key, value in sorted(node.items()):
        if key == "schema_version":
            continue

        dotted_path = "{}.{}".format(prefix, key) if prefix else key
        if isinstance(value, dict) and not is_editable_setting_path(dotted_path):
            for child_entry in _collect_persisted_entries(value, dotted_path):
                yield child_entry
            continue

        yield dotted_path, value


def _collect_generic_entries(node: JsonObject, prefix: str) -> Iterable[Tuple[str, JsonValue]]:
    for key, value in sorted(node.items()):
        dotted_path = "{}.{}".format(prefix, key)
        if isinstance(value, dict):
            for child_entry in _collect_generic_entries(value, dotted_path):
                yield child_entry
            continue
        yield dotted_path, value


def _collect_leaf_entries(node: JsonObject, prefix: Optional[str] = None) -> Iterable[Tuple[str, JsonValue]]:
    for key, value in sorted(node.items()):
        dotted_path = "{}.{}".format(prefix, key) if prefix else key
        if isinstance(value, dict) and not is_editable_setting_path(dotted_path):
            for child_entry in _collect_leaf_entries(value, dotted_path):
                yield child_entry
            continue
        yield dotted_path, value


def _group_entries_by_section(entries: Iterable[Tuple[str, JsonValue]]) -> Dict[str, List[Tuple[str, JsonValue]]]:
    grouped_entries = {}
    for dotted_path, value in entries:
        section = _section_for_path(dotted_path)
        grouped_entries.setdefault(section, []).append((dotted_path, value))
    return grouped_entries


def _section_for_path(dotted_path: str) -> str:
    definition = get_setting_definition(dotted_path)
    if definition is not None:
        return definition.section

    if dotted_path.startswith("paths."):
        return "paths"
    if dotted_path.startswith("admin."):
        return "admin"
    if dotted_path.startswith("jukebox.playback."):
        return "playback"
    if dotted_path.startswith("jukebox.reader."):
        return "reader"
    if dotted_path.startswith("jukebox.player."):
        return "player"
    return "other"


def _format_section_title(section: str) -> str:
    if section == "other":
        return "Other"
    return section.title()


def _format_entry_label(dotted_path: str) -> str:
    definition = get_setting_definition(dotted_path)
    if definition is None:
        return dotted_path
    return "{} [{}]".format(definition.label, dotted_path)


def _format_value(dotted_path: str, value: object) -> str:
    if dotted_path == "jukebox.player.sonos.selected_group":
        return _format_selected_group(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(_format_value(dotted_path, item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(", ", ": "))
    return str(value)


def _format_selected_group(value: object) -> str:
    if value is None:
        return "not configured"
    if not isinstance(value, dict):
        return str(value)

    selected_group = cast(Dict[str, object], value)
    members = selected_group.get("members")
    coordinator_uid = selected_group.get("coordinator_uid")
    if not isinstance(members, list) or not isinstance(coordinator_uid, str):
        return json.dumps(value, sort_keys=True, separators=(", ", ": "))

    member_uids = []
    for member in members:
        if not isinstance(member, dict):
            continue
        selected_member = cast(Dict[str, object], member)
        uid = selected_member.get("uid")
        if not isinstance(uid, str):
            continue
        member_uids.append(uid)

    if not member_uids:
        return json.dumps(value, sort_keys=True, separators=(", ", ": "))

    return "{} (coordinator); members: {}".format(coordinator_uid, ", ".join(member_uids))


def _build_equivalent_jukebox_admin_command(command: object, library: Optional[str] = None) -> str:
    args = ["jukebox-admin"]
    if library is not None:
        args.extend(["--library", library])

    if isinstance(command, SettingsShowCommand):
        args.extend(["settings", "show"])
        if command.effective:
            args.append("--effective")
        if command.json_output:
            args.append("--json")
        return _format_shell_command(args)

    if isinstance(command, SettingsSetCommand):
        args.extend(["settings", "set", command.dotted_path, command.value])
        if command.json_output:
            args.append("--json")
        return _format_shell_command(args)

    if isinstance(command, SettingsResetCommand):
        args.extend(["settings", "reset", command.dotted_path])
        if command.json_output:
            args.append("--json")
        return _format_shell_command(args)

    return "`jukebox-admin settings ...`"


def _format_shell_command(args: List[str]) -> str:
    return "`{}`".format(" ".join(shlex.quote(arg) for arg in args))


def _render_cli_error_message(err: BaseException) -> str:
    if isinstance(err, MalformedSettingsFileError):
        filepath = _extract_quoted_path(str(err))
        if filepath is not None:
            return "Malformed settings file at '{}'. Fix the JSON syntax and try again.".format(filepath)
        return "Malformed settings file. Fix the JSON syntax and try again."

    if isinstance(err, UnsupportedSettingsVersionError):
        return "Unsupported settings file version. {}".format(str(err))

    if isinstance(err, InvalidSettingsError):
        return _render_invalid_settings_error(err)

    if isinstance(err, SettingsError):
        return str(err)

    if isinstance(err, SystemExit) and isinstance(err.code, str):
        return _render_system_exit_message(err.code)

    return "Unexpected error. Re-run with `--verbose` for details."


def _render_invalid_settings_error(err: InvalidSettingsError) -> str:
    message = str(err)

    if message.startswith("Unsupported settings path for write: '") or message.startswith(
        "Unsupported settings path for reset: '"
    ):
        dotted_path = _extract_quoted_path(message)
        if dotted_path is not None:
            return (
                "Unsupported settings path: '{}'. Use `jukebox-admin settings show --effective --json` "
                "to inspect supported editable paths."
            ).format(dotted_path)
        return "Unsupported settings path."

    if message.startswith("Settings value for '"):
        dotted_path = _extract_quoted_path(message)
        if "must be valid JSON" in message:
            return "Invalid value for '{}'. Pass a JSON object or `null`.".format(dotted_path or "setting")
        if "must be a JSON object or null" in message:
            return "Invalid value for '{}'. Expected a JSON object or `null`.".format(dotted_path or "setting")

    if message.startswith("Invalid settings update:"):
        return "Settings update rejected: {}".format(_extract_compact_detail(message))

    if message.startswith("Invalid settings file at '"):
        filepath = _extract_quoted_path(message)
        detail = _extract_compact_detail(message)
        if filepath is not None:
            return "Persisted settings are invalid at '{}': {}".format(filepath, detail)
        return "Persisted settings are invalid: {}".format(detail)

    if message.startswith("Invalid effective settings"):
        return "Effective settings are invalid: {}".format(_extract_compact_detail(message))

    return message


def _render_system_exit_message(message: str) -> str:
    extra_name_match = re.search(r"optional `([^`]+)` dependencies", message)
    command_match = re.search(r"uv run --extra [^ ]+ ([^\n]+)", message)

    if extra_name_match is not None:
        extra_name = extra_name_match.group(1)
        install_hint = "Run `uv sync --extra {}` to install them.".format(extra_name)
        if command_match is not None:
            install_hint = "{} Or run `uv run --extra {} {}`.".format(
                install_hint,
                extra_name,
                command_match.group(1),
            )
        return "Optional `{}` dependencies are not installed. {}".format(extra_name, install_hint)

    return message


def _extract_compact_detail(message: str) -> str:
    _, _, remainder = message.partition(":")
    if remainder:
        message = remainder.strip()

    lines = [line.strip() for line in message.splitlines() if line.strip()]
    cleaned_lines = [
        _VALIDATION_SUFFIX_RE.sub("", line) for line in lines if not line.startswith("For further information visit")
    ]
    detail_lines = [
        line for line in cleaned_lines if "validation error for " not in line and "validation errors for " not in line
    ]
    if not detail_lines:
        return cleaned_lines[-1] if cleaned_lines else message

    paired_details = []
    pending_location = None
    for line in detail_lines:
        if pending_location is None:
            pending_location = line
            continue

        paired_details.append("{}: {}".format(pending_location, line))
        pending_location = None

    if paired_details:
        if pending_location is not None:
            paired_details.append(pending_location)
        return "; ".join(paired_details)

    return detail_lines[-1]


def _extract_quoted_path(message: str) -> Optional[str]:
    match = re.search(r"'([^']+)'", message)
    if match is None:
        return None
    return match.group(1)
