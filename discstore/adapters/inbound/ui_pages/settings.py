import json
from itertools import groupby
from typing import List, Optional, cast
from urllib.parse import urlencode

from fastapi import HTTPException
from fastui import AnyComponent
from fastui import components as c
from fastui.components.forms import FormFieldInput, FormFieldSelect, FormFieldTextarea
from fastui.events import GoToEvent, PageEvent
from fastui.forms import SelectOption

from jukebox.settings.definitions import (
    EditableSettingDisplay,
    build_editable_setting_displays,
    get_setting_definition,
)
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject, JsonValue

_MISSING = object()


class SettingsUIPageBuilder:
    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service

    def build_settings_success_response(self, message: str) -> list[AnyComponent]:
        query = urlencode(
            {
                "toast": "toast-settings-success",
                "toast_message": message,
            }
        )
        return [
            c.FireEvent(event=GoToEvent(url=f"/settings?{query}")),
        ]

    def reset_setting(self, setting_path: str) -> list[AnyComponent]:
        definition = get_setting_definition(setting_path)
        if definition is None:
            raise HTTPException(status_code=404, detail=f"Unknown setting path: {setting_path}")

        try:
            result = self.settings_service.reset_persisted_value(setting_path)
        except SettingsError as err:
            if not self.has_persisted_value(setting_path):
                return self.build_settings_success_response(
                    "Settings reset, but effective settings are still unavailable."
                )
            return self.build_settings_edit_page_components(setting_path, reset_error=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        return self.build_settings_success_response(str(result["message"]))

    def build_settings_page_components(
        self,
        toast: Optional[str] = None,
        toast_message: Optional[str] = None,
    ) -> List[AnyComponent]:
        settings, effective_settings_error = self.get_settings_displays()
        components: list[AnyComponent] = [
            c.Heading(text="Settings", level=1),
            c.Div(
                class_name="d-flex flex-wrap gap-2 mb-4",
                components=[
                    c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                ],
            ),
        ]
        if effective_settings_error:
            components.append(
                c.Error(
                    title="Effective settings unavailable",
                    description=(
                        f"{effective_settings_error} Persisted overrides are still shown below so you can inspect"
                        " and repair saved values."
                    ),
                )
            )

        for section, entries_iter in groupby(settings, key=lambda entry: entry.section):
            entries = list(entries_iter)
            components.extend(self.build_settings_section_components(section, entries))

        components.append(
            c.Toast(
                title="Toast",
                body=[c.Paragraph(text=toast_message or "Settings saved.")],
                open_trigger=PageEvent(name="toast-settings-success"),
                position="bottom-end",
            )
        )

        page_components: list[AnyComponent] = [c.Page(components=components)]
        if toast == "toast-settings-success":
            page_components.append(c.FireEvent(event=PageEvent(name=toast)))

        return page_components

    def build_settings_section_components(
        self,
        section: str,
        settings: List[EditableSettingDisplay],
    ) -> List[AnyComponent]:
        first_setting = settings[0]
        section_components: list[AnyComponent] = [
            c.Heading(text=first_setting.section_label, level=2),
        ]
        if first_setting.section_description:
            section_components.append(c.Paragraph(text=first_setting.section_description, class_name="mb-2"))

        section_components.append(
            c.Div(
                class_name="border rounded overflow-hidden mb-4",
                components=[self.build_settings_row(setting, index) for index, setting in enumerate(settings)],
            )
        )

        return [*section_components]

    def build_settings_row(self, setting: EditableSettingDisplay, index: int) -> AnyComponent:
        info_components: list[AnyComponent] = [
            c.Heading(text=setting.label, level=4),
            c.Paragraph(text=setting.path, class_name="text-muted small mb-1"),
            c.Paragraph(text=setting.description, class_name="mb-2"),
        ]

        badge_components = self.build_settings_badges(setting)
        if badge_components:
            info_components.append(
                c.Div(
                    class_name="d-flex flex-wrap gap-2 mb-3",
                    components=badge_components,
                )
            )
        info_components.append(self.build_settings_value_summary(setting))

        action_components: list[AnyComponent] = [
            c.Button(
                text="Edit ✏️",
                on_click=GoToEvent(url=f"/settings/{setting.path}/edit"),
                class_name="btn btn-secondary",
            )
        ]
        row_class_name = "px-3 py-3"
        if index > 0:
            row_class_name += " border-top"

        return c.Div(
            class_name=row_class_name,
            components=[
                c.Div(
                    class_name="d-flex flex-column flex-xl-row gap-3 justify-content-between align-items-xl-start",
                    components=[
                        c.Div(class_name="flex-grow-1", components=info_components),
                        c.Div(class_name="d-grid gap-2 align-self-start", components=action_components),
                    ],
                )
            ],
        )

    def build_settings_edit_page_components(
        self,
        setting_path: str,
        reset_error: Optional[str] = None,
    ) -> List[AnyComponent]:
        settings, effective_settings_error = self.get_settings_displays()
        setting = next((candidate for candidate in settings if candidate.path == setting_path), None)
        if setting is None:
            return [
                c.Page(
                    components=[
                        c.Heading(text="Edit setting", level=1),
                        c.Error(title="Setting not found", description=f"Unknown setting path: {setting_path}"),
                        c.Link(components=[c.Text(text="Back to Settings")], on_click=GoToEvent(url="/settings")),
                        c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                    ]
                )
            ]

        components: list[AnyComponent] = [
            c.Heading(text=f"Edit {setting.label}", level=1),
            c.Paragraph(
                text=f"{setting.section_label} setting", class_name="text-uppercase text-muted small fw-semibold mb-1"
            ),
            c.Paragraph(text=setting.path, class_name="text-muted small mb-1"),
            c.Paragraph(text=setting.description, class_name="mb-3"),
        ]

        badge_components = self.build_settings_badges(setting)
        if badge_components:
            components.append(
                c.Div(
                    class_name="d-flex flex-wrap gap-2 mb-3",
                    components=badge_components,
                )
            )

        if reset_error:
            components.append(
                c.Error(
                    title="Reset failed",
                    description=reset_error,
                )
            )

        if effective_settings_error:
            components.append(
                c.Error(
                    title="Effective settings unavailable",
                    description=(
                        f"{effective_settings_error} Showing persisted and default values where possible so this"
                        " setting can still be reviewed or repaired."
                    ),
                )
            )

        components.append(
            c.Div(
                class_name="border rounded p-3 mb-4 bg-light-subtle",
                components=[
                    c.Heading(text="Current values", level=3),
                    self.build_settings_value_summary(setting),
                ],
            )
        )

        components.append(
            c.Div(
                class_name="border rounded p-3 mb-4",
                components=[
                    c.Heading(text="Update override", level=3),
                    c.Paragraph(text=self.build_settings_edit_guidance(setting), class_name="mb-3"),
                    self.build_settings_edit_form(setting),
                ],
            )
        )

        if setting.is_persisted:
            components.extend(
                [
                    c.Div(
                        class_name="border rounded p-3 mb-4",
                        components=[
                            c.Heading(text="Reset override", level=3),
                            c.Paragraph(
                                text=(
                                    "Reset removes the persisted override entirely. Use it to fall back to defaults,"
                                    " environment overrides, or CLI overrides."
                                )
                            ),
                            self.build_settings_reset_form(setting.path),
                        ],
                    )
                ]
            )

        components.append(
            c.Div(
                class_name="mt-3 d-flex flex-wrap gap-3",
                components=[
                    c.Link(components=[c.Text(text="Back to Settings")], on_click=GoToEvent(url="/settings")),
                    c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                ],
            )
        )

        return [c.Page(components=components)]

    def build_settings_edit_form(self, setting: EditableSettingDisplay) -> AnyComponent:
        initial_value = setting.persisted_value if setting.is_persisted else setting.effective_value
        field_description = setting.description
        if setting.field_type == "object":
            field_description = (
                f"{field_description} Enter a JSON object matching the persisted setting shape. "
                "Leave blank to persist null. Use Reset to remove the persisted override."
            )
        if setting.requires_restart:
            field_description = f"{field_description} Takes effect after restart."

        if setting.choices:
            options: list[SelectOption] = [
                {
                    "value": choice.value,
                    "label": choice.label,
                }
                for choice in setting.choices
            ]
            form_field = FormFieldSelect(
                name="value",
                title=setting.label,
                options=options,
                initial=None if initial_value is None else str(initial_value),
                description=field_description,
                required=True,
                vanilla=True,
            )
        elif setting.field_type == "object":
            form_field = FormFieldTextarea(
                name="value",
                title=setting.label,
                initial=json.dumps(initial_value, indent=2) if initial_value is not None else "",
                description=field_description,
                required=False,
                rows=12,
                placeholder="Enter a JSON object. Leave blank to persist null.",
            )
        else:
            form_field = FormFieldInput(
                name="value",
                title=setting.label,
                initial=None if initial_value is None else str(initial_value),
                description=field_description,
                required=True,
                html_type="number" if setting.field_type == "integer" else "text",
            )

        return c.Form(
            form_fields=[form_field],
            submit_url=f"/api/ui/settings/{setting.path}",
            method="POST",
            footer=[c.Button(text="Save", html_type="submit", class_name="btn btn-primary")],
        )

    def build_settings_reset_form(self, setting_path: str) -> AnyComponent:
        return c.Form(
            form_fields=[],
            submit_url=f"/api/ui/settings/{setting_path}/reset",
            method="POST",
            footer=[c.Button(text="Reset", html_type="submit", class_name="btn btn-outline-danger text-nowrap px-3")],
        )

    def get_settings_displays(self) -> tuple[List[EditableSettingDisplay], Optional[str]]:
        persisted_settings = self.settings_service.get_persisted_settings_view()
        effective_settings_error: Optional[str] = None
        try:
            effective_settings_view = self.settings_service.get_effective_settings_view()
        except SettingsError as err:
            effective_settings_view = {}
            effective_settings_error = str(err)

        return build_editable_setting_displays(persisted_settings, effective_settings_view), effective_settings_error

    def build_settings_badges(self, setting: EditableSettingDisplay) -> list[AnyComponent]:
        badge_components: list[AnyComponent] = []
        if setting.is_pinned_default:
            badge_components.append(c.Paragraph(text="Pinned default", class_name="badge text-bg-info text-uppercase"))
        if setting.requires_restart:
            badge_components.append(
                c.Paragraph(text="Restart required", class_name="badge text-bg-warning text-uppercase")
            )
        if setting.advanced:
            badge_components.append(c.Paragraph(text="Advanced", class_name="badge text-bg-dark text-uppercase"))
        return badge_components

    def build_settings_value_summary(self, setting: EditableSettingDisplay) -> AnyComponent:
        return c.Div(
            class_name="row g-3",
            components=[
                self.build_settings_value_cell(
                    "Default",
                    self.format_settings_display_value(setting.path, setting.default_value),
                ),
                self.build_settings_value_cell(
                    "Persisted override",
                    self.format_settings_display_value(setting.path, setting.persisted_value)
                    if setting.is_persisted
                    else "None",
                ),
                self.build_settings_value_cell(
                    "Effective value",
                    self.format_settings_display_value(setting.path, setting.effective_value),
                ),
                self.build_settings_value_cell(
                    "Source",
                    self.format_settings_provenance(setting.provenance),
                ),
            ],
        )

    def build_settings_value_cell(self, label: str, value: str) -> AnyComponent:
        return c.Div(
            class_name="col-12 col-md-6 col-xl-3",
            components=[
                c.Paragraph(text=label, class_name="text-uppercase text-muted small fw-semibold mb-1"),
                c.Paragraph(text=value, class_name="mb-0 text-break"),
            ],
        )

    def build_settings_edit_guidance(self, setting: EditableSettingDisplay) -> str:
        guidance = "Save a persisted override for this setting."
        if setting.choices:
            guidance = f"{guidance} Choose one of the supported options below."
        elif setting.field_type == "object":
            guidance = (
                f"{guidance} Provide a JSON object matching the stored setting shape,"
                " or leave the field blank to persist null."
            )

        return f"{guidance} The effective value may still be superseded by environment or CLI overrides."

    def build_settings_patch(self, setting_path: str, raw_value: str) -> JsonObject:
        definition = get_setting_definition(setting_path)
        if definition is None:
            raise ValueError(f"Unknown setting path: {setting_path}")

        if definition.choices and raw_value not in {choice.value for choice in definition.choices}:
            raise ValueError("Choose a valid option.")

        if definition.field_type == "integer":
            try:
                value: JsonValue = int(raw_value)
            except ValueError as err:
                raise ValueError("Enter a valid integer.") from err
        elif definition.field_type == "number":
            try:
                value = float(raw_value)
            except ValueError as err:
                raise ValueError("Enter a valid number.") from err
        elif definition.field_type == "object":
            if raw_value.strip() == "":
                value = None
                return self.build_dotted_patch(setting_path, value)
            try:
                value = cast(JsonValue, json.loads(raw_value))
            except json.JSONDecodeError as err:
                raise ValueError("Enter valid JSON.") from err
            if not isinstance(value, dict):
                raise ValueError("Enter a JSON object.")
        else:
            value = raw_value

        return self.build_dotted_patch(setting_path, value)

    def build_dotted_patch(self, dotted_path: str, value: JsonValue) -> JsonObject:
        patch: JsonObject = {}
        cursor = patch
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            child: JsonObject = {}
            cursor[part] = child
            cursor = child
        cursor[parts[-1]] = value
        return patch

    def persisted_value_matches(self, dotted_path: str, expected_value: object) -> bool:
        return (
            self.lookup_optional_dotted_path(self.settings_service.get_persisted_settings_view(), dotted_path)
            == expected_value
        )

    def has_persisted_value(self, dotted_path: str) -> bool:
        return (
            self.lookup_optional_dotted_path(self.settings_service.get_persisted_settings_view(), dotted_path)
            is not _MISSING
        )

    def lookup_optional_dotted_path(self, root: JsonObject, dotted_path: str) -> object:
        current: JsonObject = root
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            child = current.get(part, _MISSING)
            if not isinstance(child, dict):
                return _MISSING
            current = cast(JsonObject, child)
        return current.get(parts[-1], _MISSING)

    def format_settings_display_value(self, setting_path: str, value: object) -> str:
        if value is None:
            return "null"

        definition = get_setting_definition(setting_path)
        if definition is not None and definition.choices and isinstance(value, str):
            choice_labels = {choice.value: choice.label for choice in definition.choices}
            if value in choice_labels:
                return choice_labels[value]

        if setting_path == "jukebox.player.sonos.selected_group" and isinstance(value, dict):
            selected_group = cast(dict[str, object], value)
            members = selected_group.get("members")
            coordinator_uid = selected_group.get("coordinator_uid")
            if isinstance(members, list) and isinstance(coordinator_uid, str):
                member_uids = []
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    selected_member = cast(dict[str, object], member)
                    uid = selected_member.get("uid")
                    if not isinstance(uid, str):
                        continue
                    member_uids.append(uid)
                if member_uids:
                    return "{} (coordinator); members: {}".format(coordinator_uid, ", ".join(member_uids))

        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, sort_keys=True, separators=(", ", ": "))
        except TypeError:
            return str(value)

    def format_settings_provenance(self, provenance: str) -> str:
        labels = {
            "default": "Default",
            "file": "Settings file",
            "env": "Environment override",
            "cli": "CLI override",
            "mixed": "Mixed source",
        }
        return labels.get(provenance, provenance)
