from typing import Dict

from fastapi import FastAPI, HTTPException

from discstore.domain.entities.disc import Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc

app = FastAPI()


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
        self.register_routes()

    def register_routes(self):
        @app.get("/discs", response_model=Dict[str, DiscOutput])
        def list_discs():
            return self.list_discs.execute()

        @app.post("/disc", status_code=201)
        def add_or_edit_disc(tag_id: str, disc: DiscInput):
            try:
                self.add_disc.execute(tag_id, Disc(**disc.model_dump()))
                return {"message": "Disc added"}
            except ValueError:
                self.edit_disc.execute(tag_id, Disc(**disc.model_dump()))
                return {"message": "Disc edited"}
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

        @app.delete("/disc", status_code=200)
        def remove_disc(tag_id: str):
            try:
                self.remove_disc.execute(tag_id)
                return {"message": "Disc removed"}
            except ValueError as valueErr:
                raise HTTPException(status_code=404, detail=str(valueErr))
            except Exception as err:
                raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")
