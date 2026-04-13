import asyncio
import json
from typing import AsyncIterator, List, Optional

from fastapi import Request
from fastui import AnyComponent
from fastui import components as c
from fastui.events import BackEvent, GoToEvent, PageEvent
from pydantic import BaseModel, Field

from discstore.domain.entities import CurrentTagStatus, DiscMetadata, DiscOption
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs


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


class LibraryUIPageBuilder:
    def __init__(
        self,
        list_discs: ListDiscs,
        get_disc: GetDisc,
        get_current_tag_status: GetCurrentTagStatus,
    ):
        self.list_discs = list_discs
        self.get_disc = get_disc
        self.get_current_tag_status = get_current_tag_status

    def build_index_page_components(self, toast: Optional[str] = None) -> List[AnyComponent]:
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
            *self.build_disc_library_components(discs_list),
        ]

        page_components: list[AnyComponent] = [c.Page(components=components)]

        if toast in {"toast-add-disc-success", "toast-edit-disc-success", "toast-remove-disc-success"}:
            page_components.append(c.FireEvent(event=PageEvent(name=toast)))

        return page_components

    def build_form_page_components(self, title: str, form_components: List[AnyComponent]) -> List[AnyComponent]:
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

    def build_current_tag_banner_components(
        self,
        current_tag_status: Optional[CurrentTagStatus],
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

    def build_disc_library_components(self, discs: List[DiscTable]) -> List[AnyComponent]:
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

    def build_new_disc_form_components(self, prefill_current: bool) -> List[AnyComponent]:
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

    def build_edit_disc_form_components(self, tag_id: str) -> List[AnyComponent]:
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

    def build_delete_disc_form_components(self, tag_id: str) -> List[AnyComponent]:
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

    async def current_tag_banner_event_stream(
        self,
        request: Request,
        poll_interval_seconds: float = 0.5,
    ) -> AsyncIterator[bytes]:
        previous_payload: Optional[str] = None

        while True:
            payload = self.serialize_current_tag_components(
                self.build_current_tag_banner_components(self.get_current_tag_status.execute())
            )
            if payload != previous_payload:
                previous_payload = payload
                yield f"data: {payload}\n\n".encode("utf-8")

            if await request.is_disconnected():
                break

            await asyncio.sleep(poll_interval_seconds)

    @staticmethod
    def serialize_current_tag_components(components: List[AnyComponent]) -> str:
        return json.dumps([component.model_dump(by_alias=True, exclude_none=True) for component in components])

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
