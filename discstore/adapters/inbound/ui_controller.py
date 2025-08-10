from typing import List

from fastapi.responses import HTMLResponse
from fastui import AnyComponent, FastUI, prebuilt_html
from fastui import components as c
from fastui.events import GoToEvent
from pydantic import BaseModel, Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.domain.entities.disc import Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


class DiscInput(Disc):
    pass


class DiscForm(BaseModel):
    tag: str = Field(title="Tag ID")
    uri: str = Field(title="URI / Path")
    title: str | None = Field(title="Title", default=None)
    artist: str | None = Field(title="Artist", default=None)
    album: str | None = Field(title="Album", default=None)


class UIController(APIController):
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs, remove_disc: RemoveDisc, edit_disc: EditDisc):
        # app = FastAPI()
        # super().__init__(app)
        super().__init__(add_disc, list_discs, remove_disc, edit_disc)
        self.register_routes()

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/hello", response_model=FastUI, response_model_exclude_none=True)
        def list_discs() -> List[AnyComponent]:
            discs = self.list_discs.execute()
            discs_list = [DiscForm(tag=tag, uri=disc.uri, **disc.metadata.model_dump()) for tag, disc in discs.items()]
            return [
                c.Page(
                    components=[
                        c.Heading(text="Hello World!", level=1),
                        c.Paragraph(text=f"Cette page est servie par FastUI.{discs_list[0]}"),
                        c.Link(
                            components=[c.Text(text="Voir l'API de données")],
                            on_click=GoToEvent(url="/api/v1/hello", target="_blank"),
                        ),
                        c.Table(data=discs_list),  # type: ignore
                    ]
                ),
            ]  # type: ignore

        # @self.app.get('/hello')
        # def get_hello_page() -> HTMLResponse:
        #    return HTMLResponse(
        #        prebuilt_html(
        #            title='Hello FastUI',
        #            api_root_url='/api/ui'
        #        )
        #    )

        @self.app.get("/{path:path}")
        def html_landing() -> HTMLResponse:
            return HTMLResponse(prebuilt_html(title="Discstore for Jukebox", api_root_url="api/ui"))


c.Page.model_rebuild()
