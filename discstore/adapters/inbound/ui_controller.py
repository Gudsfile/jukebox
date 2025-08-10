from typing import List

from fastapi.responses import HTMLResponse
from fastui import AnyComponent, FastUI, prebuilt_html
from fastui import components as c
from pydantic import Field

from discstore.adapters.inbound.api_controller import APIController
from discstore.domain.entities.disc import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


class DiscInput(Disc):
    pass


class DiscForm(DiscMetadata, DiscOption):
    tag: str = Field(title="Tag ID")
    uri: str = Field(title="URI / Path")


class UIController(APIController):
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs, remove_disc: RemoveDisc, edit_disc: EditDisc):
        super().__init__(add_disc, list_discs, remove_disc, edit_disc)
        self.register_routes()

    def register_routes(self):
        super().register_routes()

        @self.app.get("/api/ui/", response_model=FastUI, response_model_exclude_none=True)
        def list_discs() -> List[AnyComponent]:
            discs = self.list_discs.execute()
            discs_list = [
                DiscForm(tag=tag, uri=disc.uri, **disc.metadata.model_dump(), **disc.option.model_dump())
                for tag, disc in discs.items()
            ]
            return [
                c.Page(
                    components=[
                        c.Heading(text="DiscStore for Jukebox", level=1),
                        c.Table(data=discs_list, no_data_message="No disc found"),  # type: ignore
                    ]
                ),
            ]  # type: ignore

        @self.app.get("/{path:path}")
        def html_landing() -> HTMLResponse:
            return HTMLResponse(prebuilt_html(title="DiscStore for Jukebox", api_root_url="api/ui"))


c.Page.model_rebuild()
