import sys

if sys.version_info < (3, 8):
    raise RuntimeError("The `api_controller` module requires Python 3.8+.")

from typing import Dict

try:
    from fastapi import FastAPI, HTTPException  # type: ignore[unresolved-import]
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "The `api_controller` module requires FastAPI dependencies. Install them with: pip install gukebox[api]."
    ) from e

from discstore.domain.entities import Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class APIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs, remove_disc: RemoveDisc, edit_disc: EditDisc):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.remove_disc = remove_disc
        self.edit_disc = edit_disc
        self.app = FastAPI(
            title="DiscStore API",
            description="API for managing Jukebox disc library",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        self.register_routes()

    def register_routes(self):
        @self.app.get("/api/v1/discs", response_model=Dict[str, DiscOutput])
        def list_discs():
            return self.list_discs.execute()

        @self.app.post("/api/v1/disc", status_code=201)
        def add_or_edit_disc(tag_id: str, disc: DiscInput):
            try:
                self.add_disc.execute(tag_id, Disc(**disc.model_dump()))
                return {"message": "Disc added"}
            except ValueError:
                new_disc = Disc(**disc.model_dump())
                self.edit_disc.execute(tag_id, new_disc.uri, new_disc.metadata, new_disc.option)
                return {"message": "Disc edited"}
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @self.app.delete("/api/v1/disc", status_code=200)
        def remove_disc(tag_id: str):
            try:
                self.remove_disc.execute(tag_id)
                return {"message": "Disc removed"}
            except ValueError as valueErr:
                raise HTTPException(status_code=404, detail=str(valueErr))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")
