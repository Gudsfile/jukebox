import sys

if sys.version_info < (3, 10):
    raise RuntimeError("The `ui_controller` module requires Python 3.10+.")

from collections.abc import AsyncIterator
from typing import Annotated

from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, StreamingResponse
    from fastui import AnyComponent, FastUI, prebuilt_html
    from fastui import components as c
    from fastui.events import GoToEvent
    from fastui.forms import fastui_form
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `ui_controller` module", "ui", "jukebox-admin ui")
    ) from e

from pydantic import BaseModel, Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.adapters.inbound.ui_pages.library import DiscForm, DiscTable, LibraryUIPageBuilder
from discstore.adapters.inbound.ui_pages.settings import SettingsUIPageBuilder
from discstore.adapters.inbound.ui_pages.sonos import SonosSelectionForm, SonosUIPageBuilder
from discstore.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from jukebox.settings.definitions import (
    EditableSettingDisplay,
    get_setting_definition,
)
from jukebox.settings.errors import SettingsError
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.settings.types import JsonObject
from jukebox.sonos.discovery import SonosDiscoveryError
from jukebox.sonos.selection import SaveSonosSelection
from jukebox.sonos.service import SonosService


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
        sonos_service: SonosService,
    ):
        self.get_disc = get_disc
        self.library_pages = LibraryUIPageBuilder(
            list_discs=list_discs,
            get_disc=get_disc,
            get_current_tag_status=get_current_tag_status,
        )
        self.sonos_pages = SonosUIPageBuilder(settings_service=settings_service, sonos_service=sonos_service)
        self.settings_pages = SettingsUIPageBuilder(settings_service=settings_service)
        super().__init__(
            add_disc,
            list_discs,
            remove_disc,
            edit_disc,
            get_disc,
            get_current_tag_status,
            settings_service,
            sonos_service,
        )

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/", response_model=FastUI, response_model_exclude_none=True)
        def list_discs(toast: str | None = None) -> list[AnyComponent]:
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
        def new_disc_form(prefill: str | None = None) -> list[AnyComponent]:
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
        def edit_disc_form(tag_id: str) -> list[AnyComponent]:
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
        def delete_disc_confirmation(tag_id: str) -> list[AnyComponent]:
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
        def settings_page(toast: str | None = None, toast_message: str | None = None) -> list[AnyComponent]:
            return self._build_settings_page_components(toast=toast, toast_message=toast_message)

        @self.app.get("/api/ui/settings/{setting_path}/edit", response_model=FastUI, response_model_exclude_none=True)
        def edit_setting_form(setting_path: str) -> list[AnyComponent]:
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
                patch = self._build_settings_patch(setting_path, form.value)
                result = self.settings_service.patch_persisted_settings(patch)
            except ValueError as err:
                raise self._field_validation_error("value", str(err))
            except SettingsError as err:
                if self._persisted_value_matches(setting_path, self._lookup_optional_dotted_path(patch, setting_path)):
                    return self._build_settings_success_response(
                        "Settings saved, but effective settings are still unavailable."
                    )
                raise self._field_validation_error("value", str(err))
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self._build_settings_success_response(str(result["message"]))

        @self.app.post("/api/ui/settings/{setting_path}/reset", response_model=FastUI, response_model_exclude_none=True)
        async def reset_setting(setting_path: str) -> list[AnyComponent]:
            return self._reset_setting(setting_path)

        @self.app.get("/api/ui/sonos", response_model=FastUI, response_model_exclude_none=True)
        def sonos_page(toast: str | None = None, toast_message: str | None = None) -> list[AnyComponent]:
            return self._build_sonos_page_components(toast=toast, toast_message=toast_message)

        @self.app.get("/api/ui/sonos/edit", response_model=FastUI, response_model_exclude_none=True)
        def edit_sonos_form(
            error_message: str | None = None,
            uids: list[str] | None = None,
            coordinator_uid: str | None = None,
        ) -> list[AnyComponent]:
            field_errors = None
            if error_message:
                field_errors = {self._sonos_field_name_for_error(error_message): error_message}
            return self._build_sonos_edit_page_components(
                error_message=error_message,
                field_errors=field_errors,
                submitted_uids=uids,
                submitted_coordinator_uid=coordinator_uid,
            )

        @self.app.post("/api/ui/sonos/edit", response_model=FastUI, response_model_exclude_none=True)
        async def update_sonos_selection(
            form: Annotated[SonosSelectionForm, fastui_form(SonosSelectionForm)],
        ) -> list[AnyComponent]:
            try:
                result = SaveSonosSelection(
                    selected_group_repository=SettingsSelectedSonosGroupRepository(self.settings_service),
                    sonos_service=self.sonos_service,
                ).execute(form.uids, coordinator_uid=form.coordinator_uid)
            except SonosDiscoveryError as err:
                raise HTTPException(status_code=502, detail=str(err))
            except SettingsError as err:
                display_message = self._build_sonos_error_message(str(err), form.coordinator_uid)
                if self._persisted_sonos_selection_matches(form.uids, form.coordinator_uid):
                    return self.sonos_pages.build_sonos_success_response(
                        "Sonos selection saved, but effective settings are still unavailable."
                    )
                return self.sonos_pages.build_sonos_edit_error_response(
                    display_message,
                    form.uids,
                    form.coordinator_uid,
                )
            except ValueError as err:
                return self.sonos_pages.build_sonos_edit_error_response(
                    self._build_sonos_error_message(str(err), form.coordinator_uid),
                    form.uids,
                    form.coordinator_uid,
                )
            except HTTPException:
                raise
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

            return self.sonos_pages.build_sonos_success_response(str(result.settings_message))

        @self.app.post("/api/ui/sonos/reset", response_model=FastUI, response_model_exclude_none=True)
        async def reset_sonos_selection() -> list[AnyComponent]:
            return self._reset_sonos_selection()

        @self.app.get("/{path:path}")
        def html_landing(path: str) -> HTMLResponse:
            del path
            return HTMLResponse(prebuilt_html(title="Jukebox Admin", api_root_url="/api/ui"))

    def _build_success_response(self, toast_event_name: str) -> list[AnyComponent]:
        return [
            c.FireEvent(event=GoToEvent(url=f"/?toast={toast_event_name}")),
        ]

    def _build_settings_success_response(self, message: str) -> list[AnyComponent]:
        return self.settings_pages.build_settings_success_response(message)

    def _reset_setting(self, setting_path: str) -> list[AnyComponent]:
        return self.settings_pages.reset_setting(setting_path)

    def _build_sonos_page_components(
        self,
        toast: str | None = None,
        toast_message: str | None = None,
        error_message: str | None = None,
    ) -> list[AnyComponent]:
        return self.sonos_pages.build_sonos_page_components(
            toast=toast,
            toast_message=toast_message,
            error_message=error_message,
        )

    def _build_sonos_edit_page_components(
        self,
        error_message: str | None = None,
        field_errors: dict[str, str] | None = None,
        submitted_uids: list[str] | None = None,
        submitted_coordinator_uid: str | None = None,
    ) -> list[AnyComponent]:
        return self.sonos_pages.build_sonos_edit_page_components(
            error_message=error_message,
            field_errors=field_errors,
            submitted_uids=submitted_uids,
            submitted_coordinator_uid=submitted_coordinator_uid,
        )

    def _reset_sonos_selection(self) -> list[AnyComponent]:
        selected_group_repository = SettingsSelectedSonosGroupRepository(self.settings_service)
        try:
            result = self.settings_service.reset_persisted_value("jukebox.player.sonos.selected_group")
        except SettingsError as err:
            if selected_group_repository.get_selected_group() is None:
                return self.sonos_pages.build_sonos_success_response(
                    "Sonos selection cleared, but effective settings are still unavailable."
                )
            return self._build_sonos_page_components(error_message=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        return self.sonos_pages.build_sonos_success_response(str(result.get("message", "Settings saved.")))

    def _persisted_sonos_selection_matches(self, uids: list[str], coordinator_uid: str | None) -> bool:
        try:
            selected_group = SettingsSelectedSonosGroupRepository(self.settings_service).get_selected_group()
        except Exception:
            return False

        if selected_group is None:
            return False

        expected_coordinator_uid = coordinator_uid or (uids[0] if uids else None)
        return (
            selected_group.coordinator_uid == expected_coordinator_uid
            and [member.uid for member in selected_group.members] == uids
        )

    def _build_sonos_error_message(self, message: str, coordinator_uid: str | None) -> str:
        prefix = "Selected Sonos coordinator must be one of the selected speakers: "
        if coordinator_uid is None or not message.startswith(prefix):
            return message

        try:
            speakers = self.sonos_service.list_network_speakers()
        except Exception:
            return message

        speaker = next((speaker for speaker in speakers if speaker.uid == coordinator_uid), None)
        if speaker is None:
            return message

        return f"{prefix}{speaker.name} [{speaker.uid}]"

    def _build_index_page_components(self, toast: str | None = None) -> list[AnyComponent]:
        return self.library_pages.build_index_page_components(toast=toast)

    def _build_settings_page_components(
        self,
        toast: str | None = None,
        toast_message: str | None = None,
    ) -> list[AnyComponent]:
        return self.settings_pages.build_settings_page_components(toast=toast, toast_message=toast_message)

    def _build_settings_section_components(
        self,
        section: str,
        settings: list[EditableSettingDisplay],
    ) -> list[AnyComponent]:
        return self.settings_pages.build_settings_section_components(section, settings)

    def _build_settings_row(self, setting: EditableSettingDisplay, index: int) -> AnyComponent:
        return self.settings_pages.build_settings_row(setting, index)

    def _build_settings_edit_page_components(
        self,
        setting_path: str,
        reset_error: str | None = None,
    ) -> list[AnyComponent]:
        return self.settings_pages.build_settings_edit_page_components(setting_path, reset_error=reset_error)

    def _build_settings_edit_form(self, setting: EditableSettingDisplay) -> AnyComponent:
        return self.settings_pages.build_settings_edit_form(setting)

    def _build_settings_reset_form(self, setting_path: str) -> AnyComponent:
        return self.settings_pages.build_settings_reset_form(setting_path)

    def _get_settings_displays(self) -> tuple[list[EditableSettingDisplay], str | None]:
        return self.settings_pages.get_settings_displays()

    def _build_settings_badges(self, setting: EditableSettingDisplay) -> list[AnyComponent]:
        return self.settings_pages.build_settings_badges(setting)

    def _build_settings_value_summary(self, setting: EditableSettingDisplay) -> AnyComponent:
        return self.settings_pages.build_settings_value_summary(setting)

    def _build_settings_value_cell(self, label: str, value: str) -> AnyComponent:
        return self.settings_pages.build_settings_value_cell(label, value)

    def _build_settings_edit_guidance(self, setting: EditableSettingDisplay) -> str:
        return self.settings_pages.build_settings_edit_guidance(setting)

    def _build_settings_patch(self, setting_path: str, raw_value: str) -> JsonObject:
        return self.settings_pages.build_settings_patch(setting_path, raw_value)

    def _build_dotted_patch(self, dotted_path: str, value: object) -> JsonObject:
        return self.settings_pages.build_dotted_patch(dotted_path, value)

    def _persisted_value_matches(self, dotted_path: str, expected_value: object) -> bool:
        return self.settings_pages.persisted_value_matches(dotted_path, expected_value)

    def _has_persisted_value(self, dotted_path: str) -> bool:
        return self.settings_pages.has_persisted_value(dotted_path)

    def _lookup_optional_dotted_path(self, root: JsonObject, dotted_path: str) -> object:
        return self.settings_pages.lookup_optional_dotted_path(root, dotted_path)

    def _format_settings_display_value(self, setting_path: str, value: object) -> str:
        return self.settings_pages.format_settings_display_value(setting_path, value)

    def _format_settings_provenance(self, provenance: str) -> str:
        return self.settings_pages.format_settings_provenance(provenance)

    def _build_form_page_components(self, title: str, form_components: list[AnyComponent]) -> list[AnyComponent]:
        return self.library_pages.build_form_page_components(title=title, form_components=form_components)

    def _build_current_tag_banner_components(self, current_tag_status: CurrentTagStatus | None) -> list[AnyComponent]:
        return self.library_pages.build_current_tag_banner_components(current_tag_status)

    def _build_disc_library_components(self, discs: list[DiscTable]) -> list[AnyComponent]:
        return self.library_pages.build_disc_library_components(discs)

    def _build_disc_library_header(self) -> AnyComponent:
        return self.library_pages._build_disc_library_header()

    def _build_disc_library_row(self, disc: DiscTable) -> AnyComponent:
        return self.library_pages._build_disc_library_row(disc)

    def _build_disc_header_cell(self, label: str, class_name: str) -> AnyComponent:
        return self.library_pages._build_disc_header_cell(label, class_name)

    def _build_disc_value_cell(self, label: str, value: str | None, class_name: str) -> AnyComponent:
        return self.library_pages._build_disc_value_cell(label, value, class_name)

    def _build_new_disc_form_components(self, prefill_current: bool) -> list[AnyComponent]:
        return self.library_pages.build_new_disc_form_components(prefill_current)

    def _build_edit_disc_form_components(self, tag_id: str) -> list[AnyComponent]:
        return self.library_pages.build_edit_disc_form_components(tag_id)

    def _build_delete_disc_form_components(self, tag_id: str) -> list[AnyComponent]:
        return self.library_pages.build_delete_disc_form_components(tag_id)

    async def _current_tag_banner_event_stream(
        self,
        request: Request,
        poll_interval_seconds: float = 0.5,
    ) -> AsyncIterator[bytes]:
        async for payload in self.library_pages.current_tag_banner_event_stream(request, poll_interval_seconds):
            yield payload

    def _serialize_current_tag_components(self, components: list[AnyComponent]) -> str:
        return self.library_pages.serialize_current_tag_components(components)

    @staticmethod
    def _sonos_field_name_for_error(message: str) -> str:
        if "coordinator" in message:
            return "coordinator_uid"
        return "uids"

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
