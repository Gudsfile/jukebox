from typing import List, Optional
from urllib.parse import urlencode

from fastui import AnyComponent
from fastui import components as c
from fastui.components.forms import FormFieldSelect
from fastui.events import GoToEvent, PageEvent
from fastui.forms import SelectOption
from pydantic import BaseModel, Field, field_validator

from jukebox.settings.entities import SelectedSonosGroupSettings
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.service_protocols import SettingsService
from jukebox.sonos.discovery import DiscoveredSonosSpeaker, SonosDiscoveryError
from jukebox.sonos.selection import (
    GetSonosSelectionStatus,
    SonosSelectionStatus,
)
from jukebox.sonos.service import SonosService


class SonosSelectionForm(BaseModel):
    uids: List[str] = Field(default_factory=list, title="Speakers")
    coordinator_uid: Optional[str] = Field(None, title="Coordinator")

    @field_validator("uids", mode="before")
    @classmethod
    def coerce_single_uid_to_list(cls, value):
        if isinstance(value, str):
            return [value]
        return value


class SonosUIPageBuilder:
    def __init__(self, settings_service: SettingsService, sonos_service: SonosService):
        self.settings_service = settings_service
        self.sonos_service = sonos_service

    def build_sonos_success_response(self, message: str) -> list[AnyComponent]:
        query = urlencode(
            {
                "toast": "toast-sonos-success",
                "toast_message": message,
            }
        )
        return [
            c.FireEvent(event=GoToEvent(url=f"/sonos?{query}")),
        ]

    def build_sonos_edit_error_response(
        self,
        message: str,
        uids: List[str],
        coordinator_uid: Optional[str],
    ) -> list[AnyComponent]:
        query = urlencode(
            [
                ("error_message", message),
                *[("uids", uid) for uid in uids],
                *([("coordinator_uid", coordinator_uid)] if coordinator_uid is not None else []),
            ]
        )
        return [
            c.FireEvent(event=GoToEvent(url=f"/sonos/edit?{query}")),
        ]

    def build_sonos_page_components(
        self,
        toast: Optional[str] = None,
        toast_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> List[AnyComponent]:
        selected_group = self._get_selected_group()
        status: Optional[SonosSelectionStatus] = None
        speakers: list[DiscoveredSonosSpeaker] = []
        discovery_error = error_message

        try:
            status = GetSonosSelectionStatus(
                selected_group_repository=SettingsSelectedSonosGroupRepository(self.settings_service),
                sonos_service=self.sonos_service,
            ).execute()
            speakers = self.sonos_service.list_network_speakers()
        except SonosDiscoveryError as err:
            discovery_error = str(err)

        components: list[AnyComponent] = [
            c.Heading(text="Sonos Speakers", level=1),
            c.Div(
                class_name="d-flex flex-wrap gap-3 mb-4",
                components=[
                    c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                    c.Link(components=[c.Text(text="Back to Settings")], on_click=GoToEvent(url="/settings")),
                ],
            ),
        ]

        if discovery_error:
            components.append(
                c.Error(
                    title="Sonos discovery unavailable",
                    description=discovery_error,
                )
            )

        components.extend(self._build_saved_selection_components(status=status, selected_group=selected_group))

        action_components: list[AnyComponent] = [
            c.Button(text="Edit selection", on_click=GoToEvent(url="/sonos/edit")),
        ]
        if selected_group is not None:
            action_components.append(self._build_reset_form(button_text="Clear saved selection"))
        components.append(
            c.Div(
                class_name="d-flex flex-wrap gap-2 mb-4",
                components=action_components,
            )
        )

        if discovery_error is None:
            components.extend(
                self._build_discovered_speakers_components(speakers=speakers, selected_group=selected_group)
            )

        components.append(
            c.Toast(
                title="Toast",
                body=[c.Paragraph(text=toast_message or "Sonos settings saved.")],
                open_trigger=PageEvent(name="toast-sonos-success"),
                position="bottom-end",
            )
        )

        page_components: list[AnyComponent] = [c.Page(components=components)]
        if toast == "toast-sonos-success":
            page_components.append(c.FireEvent(event=PageEvent(name=toast)))

        return page_components

    def build_sonos_edit_page_components(
        self,
        error_message: Optional[str] = None,
        field_errors: Optional[dict[str, str]] = None,
        submitted_uids: Optional[List[str]] = None,
        submitted_coordinator_uid: Optional[str] = None,
    ) -> List[AnyComponent]:
        selected_group = self._get_selected_group()
        components: list[AnyComponent] = [
            c.Heading(text="Edit Sonos Selection", level=1),
            c.Paragraph(
                text="Choose one or more visible speakers and select the coordinator used for playback.",
                class_name="mb-3",
            ),
        ]

        try:
            speakers = self.sonos_service.list_network_speakers()
        except SonosDiscoveryError as err:
            components.append(
                c.Error(
                    title="Sonos discovery unavailable",
                    description=error_message or str(err),
                )
            )
            components.extend(self._build_navigation_links())
            return [c.Page(components=components)]

        if not speakers:
            components.append(
                c.Error(
                    title="No Sonos speakers found",
                    description="No visible Sonos speakers are currently discoverable on the network.",
                )
            )
            components.extend(self._build_navigation_links())
            return [c.Page(components=components)]

        components.append(
            c.Div(
                class_name="border rounded p-3 mb-4",
                components=[
                    c.Heading(text="Selection", level=3),
                    *self._build_edit_error_components(error_message),
                    *self._build_edit_saved_selection_components(selected_group, speakers),
                    c.Paragraph(text="Changes take effect after restart.", class_name="mb-3"),
                    self._build_selection_form(
                        speakers=speakers,
                        selected_group=selected_group,
                        field_errors=field_errors,
                        submitted_uids=submitted_uids,
                        submitted_coordinator_uid=submitted_coordinator_uid,
                    ),
                ],
            )
        )

        components.extend(self._build_navigation_links())
        return [c.Page(components=components)]

    def _build_edit_error_components(self, error_message: Optional[str]) -> list[AnyComponent]:
        if not error_message:
            return []

        return [
            c.Div(
                class_name="alert alert-danger mb-3",
                components=[
                    c.Paragraph(text="Selection not saved", class_name="fw-semibold mb-1"),
                    c.Paragraph(text=error_message, class_name="mb-0"),
                ],
            )
        ]

    def _build_edit_saved_selection_components(
        self,
        selected_group: Optional[SelectedSonosGroupSettings],
        speakers: list[DiscoveredSonosSpeaker],
    ) -> list[AnyComponent]:
        if selected_group is None:
            return []

        speakers_by_uid = {speaker.uid: speaker for speaker in speakers}
        coordinator = speakers_by_uid.get(selected_group.coordinator_uid)
        coordinator_label = (
            f"{coordinator.name} [{coordinator.uid}]" if coordinator is not None else selected_group.coordinator_uid
        )
        member_labels = [
            f"{speakers_by_uid[member.uid].name} [{member.uid}]" if member.uid in speakers_by_uid else member.uid
            for member in selected_group.members
        ]

        return [
            c.Div(
                class_name="bg-light-subtle border rounded p-3 mb-3",
                components=[
                    c.Paragraph(text="Current saved selection", class_name="text-uppercase text-muted small mb-1"),
                    c.Paragraph(text=f"Coordinator: {coordinator_label}", class_name="mb-1"),
                    c.Paragraph(text="Members: {}".format(", ".join(member_labels)), class_name="mb-0"),
                ],
            )
        ]

    def _build_selection_form(
        self,
        speakers: list[DiscoveredSonosSpeaker],
        selected_group: Optional[SelectedSonosGroupSettings],
        field_errors: Optional[dict[str, str]] = None,
        submitted_uids: Optional[List[str]] = None,
        submitted_coordinator_uid: Optional[str] = None,
    ) -> AnyComponent:
        selected_uids = (
            list(submitted_uids)
            if submitted_uids is not None
            else [member.uid for member in selected_group.members]
            if selected_group is not None
            else []
        )
        available_uids = {speaker.uid for speaker in speakers}
        initial_uids = [uid for uid in selected_uids if uid in available_uids]
        if submitted_uids is None and not initial_uids and speakers:
            initial_uids = [speakers[0].uid]

        if submitted_coordinator_uid is not None and submitted_coordinator_uid in available_uids:
            initial_coordinator_uid = submitted_coordinator_uid
        elif selected_group is not None and selected_group.coordinator_uid in available_uids:
            initial_coordinator_uid = selected_group.coordinator_uid
        else:
            initial_coordinator_uid = initial_uids[0] if initial_uids else speakers[0].uid

        speaker_options: list[SelectOption] = [
            {
                "value": speaker.uid,
                "label": self._build_speaker_option_label(speaker),
            }
            for speaker in speakers
        ]

        return c.Form(
            form_fields=[
                FormFieldSelect(
                    name="uids",
                    title="Speakers",
                    options=speaker_options,
                    initial=initial_uids,
                    description="Select the Sonos speakers that should participate in playback.",
                    required=True,
                    multiple=True,
                    error=field_errors.get("uids") if field_errors is not None else None,
                    vanilla=True,
                ),
                FormFieldSelect(
                    name="coordinator_uid",
                    title="Coordinator",
                    options=speaker_options,
                    initial=initial_coordinator_uid,
                    description="Choose the speaker that should coordinate the selected group.",
                    required=True,
                    error=field_errors.get("coordinator_uid") if field_errors is not None else None,
                    vanilla=True,
                ),
            ],
            submit_url="/api/ui/sonos/edit",
            method="POST",
            footer=[c.Button(text="Save", html_type="submit", class_name="btn btn-primary")],
        )

    def _build_saved_selection_components(
        self,
        status: Optional[SonosSelectionStatus],
        selected_group: Optional[SelectedSonosGroupSettings],
    ) -> list[AnyComponent]:
        if selected_group is None:
            return [
                c.Div(
                    class_name="border rounded p-3 mb-4 bg-light-subtle",
                    components=[
                        c.Heading(text="Saved selection", level=3),
                        c.Paragraph(text="No Sonos speaker selection is currently saved."),
                    ],
                )
            ]

        components: list[AnyComponent] = [
            c.Heading(text="Saved selection", level=3),
        ]

        if status is None:
            components.extend(
                [
                    c.Paragraph(text=f"Coordinator: {selected_group.coordinator_uid}"),
                    c.Paragraph(text="Members: {}".format(", ".join(member.uid for member in selected_group.members))),
                ]
            )
        else:
            status_label = {
                "available": "Available",
                "partial": "Partially available",
                "unavailable": "Unavailable",
                "not_selected": "Not selected",
            }.get(status.availability.status, status.availability.status)
            coordinator_label = self._format_saved_coordinator(status)
            components.append(c.Paragraph(text=f"Status: {status_label}"))
            components.append(c.Paragraph(text=f"Coordinator: {coordinator_label}"))
            components.append(
                c.Paragraph(
                    text="Members: {}".format(
                        ", ".join(self._format_status_member(member) for member in status.availability.members)
                    )
                )
            )

        return [
            c.Div(
                class_name="border rounded p-3 mb-4 bg-light-subtle",
                components=components,
            )
        ]

    def _build_discovered_speakers_components(
        self,
        speakers: list[DiscoveredSonosSpeaker],
        selected_group: Optional[SelectedSonosGroupSettings],
    ) -> list[AnyComponent]:
        if not speakers:
            return [
                c.Div(
                    class_name="border rounded p-3 mb-4",
                    components=[
                        c.Heading(text="Discovered speakers", level=3),
                        c.Paragraph(text="No visible Sonos speakers found."),
                    ],
                )
            ]

        selected_uids = {member.uid for member in selected_group.members} if selected_group is not None else set()
        coordinator_uid = selected_group.coordinator_uid if selected_group is not None else None

        return [
            c.Heading(text="Discovered speakers", level=2),
            c.Div(
                class_name="border rounded overflow-hidden mb-4",
                components=[
                    self._build_speaker_header(),
                    *[
                        self._build_speaker_row(
                            speaker=speaker,
                            is_selected=speaker.uid in selected_uids,
                            is_coordinator=speaker.uid == coordinator_uid,
                        )
                        for speaker in speakers
                    ],
                ],
            ),
        ]

    def _build_speaker_header(self) -> AnyComponent:
        return c.Div(
            class_name="d-none d-lg-block px-3 py-2 bg-light-subtle",
            components=[
                c.Div(
                    class_name="row g-2 align-items-center",
                    components=[
                        self._build_speaker_header_cell("Name", "col-lg-3"),
                        self._build_speaker_header_cell("Host", "col-lg-3"),
                        self._build_speaker_header_cell("Household", "col-lg-4"),
                        self._build_speaker_header_cell("Selection", "col-lg-2 text-lg-center"),
                    ],
                )
            ],
        )

    def _build_speaker_row(
        self,
        speaker: DiscoveredSonosSpeaker,
        is_selected: bool,
        is_coordinator: bool,
    ) -> AnyComponent:
        selection_label = "Coordinator" if is_coordinator else "Selected" if is_selected else "Available"
        return c.Div(
            class_name="px-3 py-2 border-top",
            components=[
                c.Div(
                    class_name="row g-2 align-items-center",
                    components=[
                        self._build_speaker_value_cell("Name", speaker.name, "col-12 col-lg-3"),
                        self._build_speaker_value_cell("Host", speaker.host, "col-12 col-lg-3"),
                        self._build_speaker_value_cell("Household", speaker.household_id, "col-12 col-lg-4"),
                        self._build_speaker_value_cell(
                            "Selection",
                            selection_label,
                            "col-12 col-lg-2 text-lg-center",
                        ),
                    ],
                )
            ],
        )

    def _build_speaker_header_cell(self, label: str, class_name: str) -> AnyComponent:
        return c.Div(
            class_name=f"{class_name} d-flex align-items-center",
            components=[
                c.Paragraph(text=label, class_name="text-uppercase text-muted small fw-semibold mb-0"),
            ],
        )

    def _build_speaker_value_cell(self, label: str, value: str, class_name: str) -> AnyComponent:
        return c.Div(
            class_name=class_name,
            components=[
                c.Paragraph(text=label, class_name="d-lg-none text-uppercase text-muted small fw-semibold mb-1"),
                c.Paragraph(text=value, class_name="mb-0 text-break"),
            ],
        )

    def _build_navigation_links(self) -> list[AnyComponent]:
        return [
            c.Div(
                class_name="mt-3 d-flex flex-wrap gap-3",
                components=[
                    c.Link(components=[c.Text(text="Back to Sonos")], on_click=GoToEvent(url="/sonos")),
                    c.Link(components=[c.Text(text="Back to Settings")], on_click=GoToEvent(url="/settings")),
                    c.Link(components=[c.Text(text="Back to Library")], on_click=GoToEvent(url="/")),
                ],
            )
        ]

    def _build_reset_form(self, button_text: str) -> AnyComponent:
        return c.Form(
            form_fields=[],
            submit_url="/api/ui/sonos/reset",
            method="POST",
            footer=[
                c.Button(
                    text=button_text,
                    html_type="submit",
                    class_name="btn btn-outline-danger text-nowrap px-3",
                )
            ],
        )

    def _get_selected_group(self) -> Optional[SelectedSonosGroupSettings]:
        return SettingsSelectedSonosGroupRepository(self.settings_service).get_selected_group()

    @staticmethod
    def _build_speaker_option_label(speaker: DiscoveredSonosSpeaker) -> str:
        return f"{speaker.name} ({speaker.host})"

    @staticmethod
    def _format_status_member(member) -> str:
        if member.speaker is not None:
            return f"{member.speaker.name} [{member.uid}]"
        return f"{member.uid} [unavailable]"

    @staticmethod
    def _format_saved_coordinator(status: SonosSelectionStatus) -> str:
        if status.selected_group is None:
            return "unknown"

        for member in status.availability.members:
            if member.uid == status.selected_group.coordinator_uid and member.speaker is not None:
                return f"{member.speaker.name} [{member.uid}]"
        return status.selected_group.coordinator_uid
