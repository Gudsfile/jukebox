import asyncio
import json
import sys
from itertools import groupby
from urllib.parse import urlencode

if sys.version_info < (3, 10):
    raise RuntimeError("The `ui_controller` module requires Python 3.10+.")

from typing import Annotated, AsyncIterator, List, Optional

from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, StreamingResponse
    from fastui import AnyComponent, FastUI, prebuilt_html
    from fastui import components as c
    from fastui.components.forms import FormFieldInput, FormFieldSelect, FormFieldTextarea
    from fastui.events import BackEvent, GoToEvent, PageEvent
    from fastui.forms import fastui_form
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `ui_controller` module", "ui", "discstore ui")
    ) from e
from pydantic import BaseModel, Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.settings.definitions import (
    EditableSettingDisplay,
    build_editable_setting_displays,
    get_setting_definition,
)
from jukebox.settings.errors import SettingsError
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject


class DiscTable(DiscMetadata, DiscOption):
    tag: str = Field(title="Tag ID")
    uri: str = Field(title="URI / Path")


class DiscForm(BaseModel):
    tag: str = Field(title="Tag ID")
    uri: str = Field(title="URI / Path")
    artist: Optional[str] = Field(None, title="Artist")
    album: Optional[str] = Field(None, title="Album")
    track: Optional[str] = Field(None, title="Track")
    shuffle: bool = Field(False, title="Shuffle")


class SettingValueForm(BaseModel):
    value: str = Field(title="Value")


class UIController(APIController):
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        get_current_tag_status: GetCurrentTagStatus,
        settings_service: SettingsService,
    ):
        self.get_disc = get_disc
        super().__init__(add_disc, list_discs, remove_disc, edit_disc, get_current_tag_status, settings_service)

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/", response_model=FastUI, response_model_exclude_none=True)
        def list_discs(toast: Optional[str] = None) -> List[AnyComponent]:
            return self._build_index_page_components(toast=toast)

        @self.app.get("/api/ui/current-tag-banner/events")
        async def get_current_tag_banner_events(request: Request) -> StreamingResponse:
            return StreamingResponse(
                self._current_tag_banner_event_stream(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        @self.app.get("/api/ui/discs/new", response_model=FastUI, response_model_exclude_none=True)
        def new_disc_form(prefill: Optional[str] = None) -> List[AnyComponent]:
            return self._build_form_page_components(
                title="Add disc",
                form_components=self._build_new_disc_form_components(prefill_current=(prefill == "current")),
            )

        @self.app.post("/api/ui/discs", response_model=FastUI, response_model_exclude_none=True)
        async def create_disc(disc: Annotated[DiscForm, fastui_form(DiscForm)]) -> list[AnyComponent]:
            metadata = DiscMetadata(
                artist=disc.artist,
                album=disc.album,
                track=disc.track,
            )
            option = DiscOption(shuffle=disc.shuffle)

            try:
                self.add_disc.execute(disc.tag, Disc(uri=disc.uri, metadata=metadata, option=option))
            except ValueError as err:
                raise self._field_validation_error("tag", str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_success_response("toast-add-disc-success")

        @self.app.get("/api/ui/discs/{tag_id}/edit", response_model=FastUI, response_model_exclude_none=True)
        def edit_disc_form(tag_id: str) -> List[AnyComponent]:
            return self._build_form_page_components(
                title=f"Edit disc {tag_id}",
                form_components=self._build_edit_disc_form_components(tag_id),
            )

        @self.app.post("/api/ui/discs/{tag_id}", response_model=FastUI, response_model_exclude_none=True)
        async def update_disc(
            tag_id: str,
            disc: Annotated[DiscForm, fastui_form(DiscForm)],
        ) -> list[AnyComponent]:
            metadata = DiscMetadata(
                artist=disc.artist,
                album=disc.album,
                track=disc.track,
            )
            option = DiscOption(shuffle=disc.shuffle)

            try:
                if disc.tag != tag_id:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "form": [
                                {
                                    "loc": ["tag"],
                                    "msg": "Editing tag IDs is not supported.",
                                }
                            ]
                        },
                    )
                self.edit_disc.execute(tag_id=tag_id, uri=disc.uri, metadata=metadata, option=option)
            except ValueError as err:
                raise self._field_validation_error("tag", str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_success_response("toast-edit-disc-success")

        @self.app.get("/api/ui/discs/{tag_id}/delete", response_model=FastUI, response_model_exclude_none=True)
        def delete_disc_confirmation(tag_id: str) -> List[AnyComponent]:
            return self._build_form_page_components(
                title=f"Delete disc {tag_id}",
                form_components=self._build_delete_disc_form_components(tag_id),
            )

        # Fast-UI buttons and forms do not support the DELETE method directly. So we cannot call DELETE on
        # /api/ui/discs/{tag_id}. Instead, we just use POST on /api/ui/discs/{tag_id}/delete.
        @self.app.post("/api/ui/discs/{tag_id}/delete", response_model=FastUI, response_model_exclude_none=True)
        async def delete_disc(tag_id: str) -> list[AnyComponent]:
            try:
                self.remove_disc.execute(tag_id)
            except ValueError as err:
                raise HTTPException(status_code=404, detail=str(err))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_success_response("toast-remove-disc-success")

        @self.app.get("/api/ui/settings", response_model=FastUI, response_model_exclude_none=True)
        def settings_page(toast: Optional[str] = None, toast_message: Optional[str] = None) -> List[AnyComponent]:
            return self._build_settings_page_components(toast=toast, toast_message=toast_message)

        @self.app.get("/api/ui/settings/{setting_path}/edit", response_model=FastUI, response_model_exclude_none=True)
        def edit_setting_form(setting_path: str) -> List[AnyComponent]:
            return self._build_settings_edit_page_components(setting_path)

        @self.app.post("/api/ui/settings/{setting_path}", response_model=FastUI, response_model_exclude_none=True)
        async def update_setting(
            setting_path: str,
            form: Annotated[SettingValueForm, fastui_form(SettingValueForm)],
        ) -> list[AnyComponent]:
            definition = get_setting_definition(setting_path)
            if definition is None:
                raise HTTPException(status_code=404, detail=f"Unknown setting path: {setting_path}")

            try:
                result = self.settings_service.patch_persisted_settings(
                    self._build_settings_patch(setting_path, form.value)
                )
            except ValueError as err:
                raise self._field_validation_error("value", str(err))
            except SettingsError as err:
                raise self._field_validation_error("value", str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_settings_success_response(str(result["message"]))

        @self.app.post("/api/ui/settings/{setting_path}/reset", response_model=FastUI, response_model_exclude_none=True)
        async def reset_setting(setting_path: str) -> list[AnyComponent]:
            definition = get_setting_definition(setting_path)
            if definition is None:
                raise HTTPException(status_code=404, detail=f"Unknown setting path: {setting_path}")

            try:
                result = self.settings_service.reset_persisted_value(setting_path)
            except SettingsError as err:
                raise self._field_validation_error("path", str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_settings_success_response(str(result["message"]))

        @self.app.get("/{path:path}")
        def html_landing(path: str) -> HTMLResponse:
            del path
            return HTMLResponse(prebuilt_html(title="DiscStore for Jukebox", api_root_url="/api/ui"))

    def _build_success_response(self, toast_event_name: str) -> list[AnyComponent]:
        return [
            c.FireEvent(event=GoToEvent(url=f"/?toast={toast_event_name}")),
        ]

    def _build_settings_success_response(self, message: str) -> list[AnyComponent]:
        query = urlencode(
            {
                "toast": "toast-settings-success",
                "toast_message": message,
            }
        )
        return [
            c.FireEvent(event=GoToEvent(url=f"/settings?{query}")),
        ]

    def _build_index_page_components(self, toast: Optional[str] = None) -> List[AnyComponent]:
        discs = self.list_discs.execute()
        discs_list = [
            DiscTable(tag=tag, uri=disc.uri, **disc.metadata.model_dump(), **disc.option.model_dump())
            for tag, disc in discs.items()
        ]

        components: list[AnyComponent] = [
            c.Heading(text="DiscStore for Jukebox", level=1),
            c.Paragraph(text=f"📀 {len(discs)} disc(s) in library"),
            c.ServerLoad(
                path="/current-tag-banner/events",
                sse=True,
                sse_retry=2000,
            ),
            c.Div(
                class_name="d-flex flex-wrap gap-2",
                components=[
                    c.Button(text="➕ Add a new disc", on_click=GoToEvent(url="/discs/new")),
                    c.Button(text="⚙️ Settings", on_click=GoToEvent(url="/settings"), class_name="btn btn-secondary"),
                ],
            ),
            c.Toast(
                title="Toast",
                body=[c.Paragraph(text="🎉 Disc added")],
                open_trigger=PageEvent(name="toast-add-disc-success"),
                position="bottom-end",
            ),
            c.Toast(
                title="Toast",
                body=[c.Paragraph(text="🎉 Disc edited")],
                open_trigger=PageEvent(name="toast-edit-disc-success"),
                position="bottom-end",
            ),
            c.Toast(
                title="Toast",
                body=[c.Paragraph(text="🗑️ Disc removed")],
                open_trigger=PageEvent(name="toast-remove-disc-success"),
                position="bottom-end",
            ),
            *self._build_disc_library_components(discs_list),
        ]

        page_components: list[AnyComponent] = [c.Page(components=components)]

        if toast in {"toast-add-disc-success", "toast-edit-disc-success", "toast-remove-disc-success"}:
            page_components.append(c.FireEvent(event=PageEvent(name=toast)))

        return page_components

    def _build_settings_page_components(
        self,
        toast: Optional[str] = None,
        toast_message: Optional[str] = None,
    ) -> List[AnyComponent]:
        settings = self._get_settings_displays()
        components: list[AnyComponent] = [
            c.Heading(text="Settings", level=1),
            c.Paragraph(text="Manage shared admin and jukebox settings from the same backend used by the CLI and API."),
            c.Div(
                class_name="d-flex flex-wrap gap-2 mb-4",
                components=[
                    c.Button(text="Back to Library", on_click=GoToEvent(url="/"), class_name="btn btn-secondary"),
                ],
            ),
        ]

        for section, entries_iter in groupby(settings, key=lambda entry: entry.section):
            entries = list(entries_iter)
            components.extend(self._build_settings_section_components(section, entries))

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

    def _build_settings_section_components(
        self,
        section: str,
        settings: List[EditableSettingDisplay],
    ) -> List[AnyComponent]:
        return [
            c.Heading(text=section.title(), level=2),
            c.Div(
                class_name="border rounded overflow-hidden mb-4",
                components=[self._build_settings_row(setting, index) for index, setting in enumerate(settings)],
            ),
        ]

    def _build_settings_row(self, setting: EditableSettingDisplay, index: int) -> AnyComponent:
        info_components: list[AnyComponent] = [
            c.Heading(text=setting.label, level=4),
            c.Paragraph(text=setting.path, class_name="text-muted small mb-1"),
            c.Paragraph(text=setting.description, class_name="mb-2"),
            c.Paragraph(
                text="Persisted: {}".format(self._format_settings_display_value(setting.path, setting.persisted_value))
                if setting.is_persisted
                else "Persisted: Not persisted",
                class_name="mb-1",
            ),
            c.Paragraph(
                text="Effective: {}".format(self._format_settings_display_value(setting.path, setting.effective_value)),
                class_name="mb-1",
            ),
            c.Paragraph(text=f"Source: {setting.provenance}", class_name="mb-0"),
        ]

        badge_components: list[AnyComponent] = []
        if setting.is_pinned_default:
            badge_components.append(c.Paragraph(text="Pinned default", class_name="badge text-bg-info text-uppercase"))
        if setting.requires_restart:
            badge_components.append(
                c.Paragraph(text="Restart required", class_name="badge text-bg-warning text-uppercase")
            )
        if badge_components:
            info_components.append(
                c.Div(
                    class_name="d-flex flex-wrap gap-2 mt-2",
                    components=badge_components,
                )
            )

        action_components: list[AnyComponent] = [
            c.Button(
                text="Edit",
                on_click=GoToEvent(url=f"/settings/{setting.path}/edit"),
                class_name="btn btn-secondary",
            )
        ]
        if setting.is_persisted:
            action_components.append(self._build_settings_reset_form(setting.path))

        row_class_name = "px-3 py-3"
        if index > 0:
            row_class_name += " border-top"

        return c.Div(
            class_name=row_class_name,
            components=[
                c.Div(
                    class_name="d-flex flex-column flex-lg-row gap-3 justify-content-between align-items-lg-start",
                    components=[
                        c.Div(class_name="flex-grow-1", components=info_components),
                        c.Div(class_name="d-flex flex-wrap gap-2", components=action_components),
                    ],
                )
            ],
        )

    def _build_settings_edit_page_components(self, setting_path: str) -> List[AnyComponent]:
        setting = self._get_setting_display(setting_path)
        if setting is None:
            return [
                c.Page(
                    components=[
                        c.Heading(text="Edit setting", level=1),
                        c.Error(title="Setting not found", description=f"Unknown setting path: {setting_path}"),
                        c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                    ]
                )
            ]

        components: list[AnyComponent] = [
            c.Heading(text=f"Edit {setting.label}", level=1),
            c.Paragraph(text=setting.path, class_name="text-muted small mb-1"),
            c.Paragraph(
                text="Current persisted value: {}".format(
                    self._format_settings_display_value(setting.path, setting.persisted_value)
                )
                if setting.is_persisted
                else "Current persisted value: Not persisted",
                class_name="mb-1",
            ),
            c.Paragraph(
                text="Current effective value: {}".format(
                    self._format_settings_display_value(setting.path, setting.effective_value)
                ),
                class_name="mb-1",
            ),
            c.Paragraph(text=f"Source: {setting.provenance}", class_name="mb-0"),
        ]

        badge_components: list[AnyComponent] = []
        if setting.is_pinned_default:
            badge_components.append(c.Paragraph(text="Pinned default", class_name="badge text-bg-info text-uppercase"))
        if setting.requires_restart:
            badge_components.append(
                c.Paragraph(text="Restart required", class_name="badge text-bg-warning text-uppercase")
            )
        if badge_components:
            components.append(
                c.Div(
                    class_name="d-flex flex-wrap gap-2 mt-2",
                    components=badge_components,
                )
            )

        components.append(self._build_settings_edit_form(setting))

        if setting.is_persisted:
            components.extend(
                [
                    c.Heading(text="Reset override", level=3),
                    c.Paragraph(
                        text="Reset removes the persisted override entirely. Use it to unpin a default value or fall back to merged defaults and overrides."
                    ),
                    self._build_settings_reset_form(setting.path),
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

    def _build_settings_edit_form(self, setting: EditableSettingDisplay) -> AnyComponent:
        initial_value = setting.persisted_value if setting.is_persisted else setting.effective_value
        field_description = setting.description
        if setting.field_type == "object":
            field_description = (
                f"{field_description} Leave blank to persist null. Use Reset to remove the persisted override."
            )
        if setting.requires_restart:
            field_description = f"{field_description} Takes effect after restart."

        if setting.choices:
            form_field = FormFieldSelect(
                name="value",
                title=setting.label,
                options=[
                    {
                        "value": choice.value,
                        "label": choice.label,
                    }
                    for choice in setting.choices
                ],
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
                html_type="number" if setting.field_type in {"integer", "number"} else "text",
            )

        return c.Form(
            form_fields=[form_field],
            submit_url=f"/api/ui/settings/{setting.path}",
            method="POST",
            footer=[c.Button(text="Save", html_type="submit", class_name="btn btn-primary")],
        )

    def _build_settings_reset_form(self, setting_path: str) -> AnyComponent:
        return c.Form(
            form_fields=[],
            submit_url=f"/api/ui/settings/{setting_path}/reset",
            method="POST",
            display_mode="inline",
            footer=[c.Button(text="Reset", html_type="submit", class_name="btn btn-outline-danger")],
        )

    def _get_settings_displays(self) -> List[EditableSettingDisplay]:
        return build_editable_setting_displays(
            self.settings_service.get_persisted_settings_view(),
            self.settings_service.get_effective_settings_view(),
        )

    def _get_setting_display(self, setting_path: str) -> Optional[EditableSettingDisplay]:
        return next((setting for setting in self._get_settings_displays() if setting.path == setting_path), None)

    def _build_settings_patch(self, setting_path: str, raw_value: str) -> JsonObject:
        definition = get_setting_definition(setting_path)
        if definition is None:
            raise ValueError(f"Unknown setting path: {setting_path}")

        if definition.choices and raw_value not in {choice.value for choice in definition.choices}:
            raise ValueError("Choose a valid option.")

        if definition.field_type == "integer":
            try:
                value: object = int(raw_value)
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
                return self._build_dotted_patch(setting_path, value)
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError as err:
                raise ValueError("Enter valid JSON.") from err
        else:
            value = raw_value

        return self._build_dotted_patch(setting_path, value)

    def _build_dotted_patch(self, dotted_path: str, value: object) -> JsonObject:
        patch: JsonObject = {}
        cursor = patch
        parts = dotted_path.split(".")
        for part in parts[:-1]:
            child: JsonObject = {}
            cursor[part] = child
            cursor = child
        cursor[parts[-1]] = value
        return patch

    def _format_settings_display_value(self, setting_path: str, value: object) -> str:
        if value is None:
            return "null"

        if setting_path == "jukebox.player.sonos.selected_group" and isinstance(value, dict):
            members = value.get("members")
            coordinator_uid = value.get("coordinator_uid")
            if isinstance(members, list) and isinstance(coordinator_uid, str):
                member_names = []
                coordinator_name = coordinator_uid
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    name = member.get("name") or member.get("uid")
                    if not isinstance(name, str):
                        continue
                    member_names.append(name)
                    if member.get("uid") == coordinator_uid:
                        coordinator_name = name
                if member_names:
                    return "{} (coordinator); members: {}".format(coordinator_name, ", ".join(member_names))

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

    def _build_form_page_components(self, title: str, form_components: List[AnyComponent]) -> List[AnyComponent]:
        return [
            c.Page(
                components=[
                    c.Heading(text=title, level=1),
                    *form_components,
                    c.Div(
                        class_name="mt-3",
                        components=[
                            c.Link(
                                components=[c.Text(text="Back to Library")],
                                on_click=GoToEvent(url="/"),
                            )
                        ],
                    ),
                ]
            )
        ]

    def _build_current_tag_banner_components(
        self, current_tag_status: Optional[CurrentTagStatus]
    ) -> List[AnyComponent]:
        if current_tag_status is None:
            return []

        if current_tag_status.known_in_library:
            return [
                c.Div(
                    class_name="alert alert-info mb-3 d-flex flex-column flex-md-row gap-3 justify-content-between align-items-md-center",
                    components=[
                        c.Div(
                            class_name="mb-0",
                            components=[
                                c.Heading(text="Known disc on reader", level=4),
                                c.Paragraph(text=f'Tag "{current_tag_status.tag_id}" is already in the library.'),
                            ],
                        ),
                        c.Button(
                            text="Edit this disc",
                            on_click=GoToEvent(url=f"/discs/{current_tag_status.tag_id}/edit"),
                        ),
                    ],
                )
            ]

        return [
            c.Div(
                class_name="alert alert-warning mb-3 d-flex flex-column flex-md-row gap-3 justify-content-between align-items-md-center",
                components=[
                    c.Div(
                        class_name="mb-0",
                        components=[
                            c.Heading(text="Unknown disc on reader", level=4),
                            c.Paragraph(text=f'Tag "{current_tag_status.tag_id}" is ready to be added to the library.'),
                        ],
                    ),
                    c.Button(text="Add this disc", on_click=GoToEvent(url="/discs/new?prefill=current")),
                ],
            )
        ]

    def _build_disc_library_components(self, discs: List[DiscTable]) -> List[AnyComponent]:
        if not discs:
            return [c.Paragraph(text="No disc found")]

        return [
            c.Div(
                class_name="border rounded mt-3 mb-5 overflow-hidden",
                components=[
                    self._build_disc_library_header(),
                    *[self._build_disc_library_row(disc) for disc in discs],
                ],
            )
        ]

    def _build_disc_library_header(self) -> AnyComponent:
        return c.Div(
            class_name="d-none d-lg-block px-3 py-2 bg-light-subtle",
            components=[
                c.Div(
                    class_name="row g-2 align-items-center",
                    components=[
                        self._build_disc_header_cell("Tag ID", "col-lg"),
                        self._build_disc_header_cell("URI / Path", "col-lg-3"),
                        self._build_disc_header_cell("Artist", "col-lg-2 text-lg-center"),
                        self._build_disc_header_cell("Album", "col-lg-2 text-lg-center"),
                        self._build_disc_header_cell("Track", "col-lg-2 text-lg-center"),
                        self._build_disc_header_cell("Shuffle", "col-lg-1 text-lg-center"),
                        c.Div(
                            class_name="col-lg-auto d-flex justify-content-lg-end",
                            components=[
                                c.Button(
                                    text="Edit ✏️",
                                    class_name="btn btn-secondary invisible",
                                )
                            ],
                        ),
                    ],
                )
            ],
        )

    def _build_disc_library_row(self, disc: DiscTable) -> AnyComponent:
        return c.Div(
            class_name="px-3 py-2 border-top",
            components=[
                c.Div(
                    class_name="row g-2 align-items-center",
                    components=[
                        self._build_disc_value_cell("Tag ID", disc.tag, "col-12 col-lg"),
                        self._build_disc_value_cell("URI / Path", disc.uri, "col-12 col-lg-3"),
                        self._build_disc_value_cell("Artist", disc.artist, "col-6 col-md-3 col-lg-2 text-lg-center"),
                        self._build_disc_value_cell("Album", disc.album, "col-6 col-md-3 col-lg-2 text-lg-center"),
                        self._build_disc_value_cell("Track", disc.track, "col-6 col-md-3 col-lg-2 text-lg-center"),
                        self._build_disc_value_cell(
                            "Shuffle", "✓" if disc.shuffle else "×", "col-6 col-md-3 col-lg-1 text-lg-center"
                        ),
                        c.Div(
                            class_name="col-12 col-lg-auto d-flex justify-content-lg-end",
                            components=[
                                c.Button(
                                    text="Edit ✏️",
                                    on_click=GoToEvent(url=f"/discs/{disc.tag}/edit"),
                                    class_name="btn btn-secondary",
                                ),
                            ],
                        ),
                    ],
                )
            ],
        )

    def _build_disc_header_cell(self, label: str, class_name: str) -> AnyComponent:
        justify_class = "justify-content-lg-start"
        if "text-lg-center" in class_name:
            justify_class = "justify-content-lg-center"
        elif "text-lg-end" in class_name:
            justify_class = "justify-content-lg-end"

        return c.Div(
            class_name=f"{class_name} d-flex align-items-center {justify_class}",
            components=[
                c.Paragraph(text=label, class_name="text-uppercase text-muted small fw-semibold mb-0"),
            ],
        )

    def _build_disc_value_cell(self, label: str, value: Optional[str], class_name: str) -> AnyComponent:
        return c.Div(
            class_name=class_name,
            components=[
                c.Paragraph(text=label, class_name="d-lg-none text-uppercase text-muted small fw-semibold mb-1"),
                c.Paragraph(text=value or "—", class_name="mb-0 text-break"),
            ],
        )

    def _build_new_disc_form_components(self, prefill_current: bool) -> List[AnyComponent]:
        initial = None

        if prefill_current:
            current_tag_status = self.get_current_tag_status.execute()
            if current_tag_status is None:
                return [
                    c.Error(
                        title="No current tag available",
                        description="There is no tag on the reader right now, so the form cannot be prefilled.",
                    )
                ]
            if current_tag_status.known_in_library:
                return [
                    c.Error(
                        title="Current tag already known",
                        description=f'Tag "{current_tag_status.tag_id}" is already in the library.',
                    )
                ]
            initial = {"tag": current_tag_status.tag_id, "shuffle": False}

        return [
            c.ModelForm(
                model=DiscForm,
                submit_url="/api/ui/discs",
                method="POST",
                initial=initial,
            )
        ]

    def _build_edit_disc_form_components(self, tag_id: str) -> List[AnyComponent]:
        if not tag_id:
            return [
                c.Error(
                    title="No disc selected",
                    description="Edit mode requires an existing disc tag ID.",
                )
            ]
        try:
            disc = self.get_disc.execute(tag_id)
        except ValueError as err:
            return [
                c.Error(
                    title="Disc not found",
                    description=str(err),
                )
            ]

        return [
            c.ModelForm(
                model=DiscForm,
                submit_url=f"/api/ui/discs/{tag_id}",
                method="POST",
                initial={
                    "tag": tag_id,
                    "uri": disc.uri,
                    "artist": disc.metadata.artist,
                    "album": disc.metadata.album,
                    "track": disc.metadata.track,
                    "shuffle": disc.option.shuffle,
                },
            ),
            c.Button(
                text="🗑️ Delete this disc",
                on_click=GoToEvent(url=f"/discs/{tag_id}/delete"),
                class_name="btn btn-danger mt-3",
            ),
        ]

    def _build_delete_disc_form_components(self, tag_id: str) -> List[AnyComponent]:
        if not tag_id:
            return [c.Error(title="No disc selected", description="Delete mode requires an existing disc tag ID.")]
        try:
            _ = self.get_disc.execute(tag_id)
        except ValueError as err:
            return [c.Error(title="Disc not found", description=str(err))]

        return [
            c.Paragraph(text=f'Are you sure you want to delete the disc with tag "{tag_id}"?'),
            c.Div(
                class_name="alert alert-danger",
                components=[c.Paragraph(text="This action cannot be undone.")],
            ),
            c.Div(
                class_name="d-flex gap-2 mt-3",
                components=[
                    c.Form(
                        form_fields=[],
                        submit_url=f"/api/ui/discs/{tag_id}/delete",
                        method="POST",
                    ),
                    c.Button(
                        text="Cancel",
                        on_click=BackEvent(),
                        class_name="btn btn-secondary",
                    ),
                ],
            ),
        ]

    async def _current_tag_banner_event_stream(
        self,
        request: Request,
        poll_interval_seconds: float = 0.5,
    ) -> AsyncIterator[bytes]:
        previous_payload: Optional[str] = None

        while True:
            payload = self._serialize_current_tag_components(
                self._build_current_tag_banner_components(self.get_current_tag_status.execute())
            )
            if payload != previous_payload:
                previous_payload = payload
                yield f"data: {payload}\n\n".encode("utf-8")

            if await request.is_disconnected():
                break

            await asyncio.sleep(poll_interval_seconds)

    def _serialize_current_tag_components(self, components: List[AnyComponent]) -> str:
        return json.dumps([component.model_dump(by_alias=True, exclude_none=True) for component in components])

    def _field_validation_error(self, field_name: str, message: str) -> HTTPException:
        return HTTPException(
            status_code=422,
            detail={
                "form": [
                    {
                        "loc": [field_name],
                        "msg": message,
                    }
                ]
            },
        )


c.Page.model_rebuild()
