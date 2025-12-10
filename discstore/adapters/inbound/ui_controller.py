import sys

if sys.version_info < (3, 10):
    raise RuntimeError("The `ui_controller` module requires Python 3.10+.")

import uuid
from typing import Annotated, List, Optional

try:
    from fastapi import HTTPException  # type: ignore[unresolved-import]
    from fastapi.responses import HTMLResponse  # type: ignore[unresolved-import]
    from fastui import AnyComponent, FastUI, prebuilt_html  # type: ignore[unresolved-import]
    from fastui import components as c  # type: ignore[unresolved-import]
    from fastui.events import GoToEvent, PageEvent  # type: ignore[unresolved-import]
    from fastui.forms import fastui_form  # type: ignore[unresolved-import]
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "The `ui_controller` module requires FastUI dependency. Install it with: pip install gukebox[ui]."
    ) from e
from pydantic import BaseModel, Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.domain.entities import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


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
    ):
        super().__init__(add_disc, list_discs, remove_disc, edit_disc)
        self.register_routes()

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/", response_model=FastUI, response_model_exclude_none=True)
        def list_discs() -> List[AnyComponent]:
            discs = self.list_discs.execute()

            discs_list = [
                DiscTable(tag=tag, uri=disc.uri, **disc.metadata.model_dump(), **disc.option.model_dump())
                for tag, disc in discs.items()
            ]

            return [
                c.Page(
                    components=[
                        c.Heading(text="DiscStore for Jukebox", level=1),
                        c.Paragraph(text=f"📀 {len(discs)} disc(s) in library"),
                        c.Button(text="➕ Add a new disc", on_click=PageEvent(name="modal-add-disc")),
                        c.Modal(
                            title="➕ Add a new disc",
                            body=[
                                c.ModelForm(model=DiscForm, submit_url="/modal-add-or-edit-disc", method="POST"),
                            ],
                            footer=None,
                            open_trigger=PageEvent(name="modal-add-disc"),
                        ),
                        c.Toast(
                            title="Toast",
                            body=[c.Paragraph(text="🎉 Disc added")],
                            open_trigger=PageEvent(name="toast-add-disc-success"),
                            position="top-center",
                        ),
                        c.Toast(
                            title="Toast",
                            body=[c.Paragraph(text="🎉 Disc edited")],
                            open_trigger=PageEvent(name="toast-edit-disc-success"),
                            position="top-center",
                        ),
                        c.Table(
                            data=discs_list,
                            no_data_message="No disc found",
                        ),  # type: ignore
                    ]
                ),
            ]  # type: ignore

        @self.app.post("/modal-add-or-edit-disc", response_model=FastUI, response_model_exclude_none=True)
        async def modal_add_or_edit_disc(disc: Annotated[DiscForm, fastui_form(DiscForm)]) -> list[AnyComponent]:
            try:
                # Create metadata from form fields
                metadata = DiscMetadata(
                    artist=disc.artist,
                    album=disc.album,
                    track=disc.track,
                )
                option = DiscOption(shuffle=disc.shuffle)

                try:
                    self.add_disc.execute(disc.tag, Disc(uri=disc.uri, metadata=metadata, option=option))
                    return [
                        c.FireEvent(event=PageEvent(name="modal-add-disc", clear=True)),
                        c.FireEvent(event=PageEvent(name="toast-add-disc-success")),
                        c.FireEvent(event=GoToEvent(url=f"/?refresh={uuid.uuid4()}")),
                    ]
                except ValueError:
                    # Disc exists, update it
                    self.edit_disc.execute(
                        tag_id=disc.tag,
                        uri=disc.uri,
                        metadata=metadata,
                        option=option,
                    )
                    return [
                        c.FireEvent(event=PageEvent(name="modal-add-disc", clear=True)),
                        c.FireEvent(event=PageEvent(name="toast-edit-disc-success")),
                        c.FireEvent(event=GoToEvent(url=f"/?refresh={uuid.uuid4()}")),
                    ]
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.get("/")
        def html_landing() -> HTMLResponse:
            return HTMLResponse(prebuilt_html(title="DiscStore for Jukebox", api_root_url="/api/ui"))


c.Page.model_rebuild()
