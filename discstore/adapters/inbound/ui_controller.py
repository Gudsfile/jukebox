import asyncio
import json
import sys

if sys.version_info < (3, 10):
    raise RuntimeError("The `ui_controller` module requires Python 3.10+.")

from typing import Annotated, AsyncIterator, List, Optional

from jukebox.shared.dependency_messages import optional_extra_dependency_message

try:
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, StreamingResponse
    from fastui import AnyComponent, FastUI, prebuilt_html
    from fastui import components as c
    from fastui.events import GoToEvent, PageEvent
    from fastui.forms import fastui_form
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        optional_extra_dependency_message("The `ui_controller` module", "ui", "discstore ui")
    ) from e
from pydantic import BaseModel, Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.domain.entities import CurrentDisc, Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_disc import GetCurrentDisc
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc
from discstore.domain.use_cases.update_current_disc_library_status import UpdateCurrentDiscLibraryStatus


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


class UIController(APIController):
    def __init__(
        self,
        add_disc: AddDisc,
        list_discs: ListDiscs,
        remove_disc: RemoveDisc,
        edit_disc: EditDisc,
        get_disc: GetDisc,
        get_current_disc: GetCurrentDisc,
        update_current_disc_library_status: UpdateCurrentDiscLibraryStatus,
    ):
        self.get_disc = get_disc
        self.update_current_disc_library_status = update_current_disc_library_status
        super().__init__(add_disc, list_discs, remove_disc, edit_disc, get_current_disc)

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/", response_model=FastUI, response_model_exclude_none=True)
        def list_discs(toast: Optional[str] = None) -> List[AnyComponent]:
            return self._build_index_page_components(toast=toast)

        @self.app.get("/api/ui/current-disc-banner/events")
        async def get_current_disc_banner_events(request: Request) -> StreamingResponse:
            return StreamingResponse(
                self._current_disc_banner_event_stream(request),
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
                self.update_current_disc_library_status.execute(disc.tag, True)
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

        @self.app.get("/{path:path}")
        def html_landing(path: str) -> HTMLResponse:
            del path
            return HTMLResponse(prebuilt_html(title="DiscStore for Jukebox", api_root_url="/api/ui"))

    def _build_success_response(self, toast_event_name: str) -> list[AnyComponent]:
        return [
            c.FireEvent(event=GoToEvent(url=f"/?toast={toast_event_name}")),
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
                path="/current-disc-banner/events",
                sse=True,
                sse_retry=2000,
            ),
            c.Button(text="➕ Add a new disc", on_click=GoToEvent(url="/discs/new")),
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
            *self._build_disc_library_components(discs_list),
        ]

        page_components: list[AnyComponent] = [c.Page(components=components)]

        if toast in {"toast-add-disc-success", "toast-edit-disc-success"}:
            page_components.append(c.FireEvent(event=PageEvent(name=toast)))

        return page_components

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

    def _build_current_disc_banner_components(self, current_disc: Optional[CurrentDisc]) -> List[AnyComponent]:
        if current_disc is None:
            return []

        if current_disc.known_in_library:
            return [
                c.Div(
                    class_name="alert alert-info mb-3",
                    components=[
                        c.Heading(text="Known disc on reader", level=4),
                        c.Paragraph(text=f'Tag "{current_disc.tag_id}" is already in the library.'),
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
                            c.Paragraph(text=f'Tag "{current_disc.tag_id}" is ready to be added to the library.'),
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
            ]
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
            current_disc = self.get_current_disc.execute()
            if current_disc is None:
                return [
                    c.Error(
                        title="No current disc available",
                        description="There is no tag on the reader right now, so the form cannot be prefilled.",
                    )
                ]
            if current_disc.known_in_library:
                return [
                    c.Error(
                        title="Current disc already known",
                        description=f'Tag "{current_disc.tag_id}" is already in the library.',
                    )
                ]
            initial = {"tag": current_disc.tag_id, "shuffle": False}

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
            )
        ]

    async def _current_disc_banner_event_stream(
        self,
        request: Request,
        poll_interval_seconds: float = 0.5,
    ) -> AsyncIterator[bytes]:
        previous_payload: Optional[str] = None

        while True:
            payload = self._serialize_current_disc_components(
                self._build_current_disc_banner_components(self.get_current_disc.execute())
            )
            if payload != previous_payload:
                previous_payload = payload
                yield f"data: {payload}\n\n".encode("utf-8")

            if await request.is_disconnected():
                break

            await asyncio.sleep(poll_interval_seconds)

    def _serialize_current_disc_components(self, components: List[AnyComponent]) -> str:
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
