from typing import Dict

from fastapi import FastAPI, HTTPException

from discstore.domain.entities.disc import Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.list_discs import ListDiscs

app = FastAPI()


class DiscInput(Disc):
    pass


class DiscOutput(Disc):
    pass


class APIController:
    def __init__(self, add_disc: AddDisc, list_discs: ListDiscs):
        self.add_disc = add_disc
        self.list_discs = list_discs
        self.register_routes()

    def register_routes(self):
        @app.get("/discs", response_model=Dict[str, DiscOutput])
        def list_discs():
            return self.list_discs.execute()

        @app.post("/discs", status_code=201)
        def add_disc(tag_id: str, disc: DiscInput):
            try:
                self.add_disc.execute(tag_id, Disc(**disc.model_dump()))
                return {"message": "Disc added"}
            except ValueError as valueErr:
                raise HTTPException(status_code=400, detail=str(valueErr))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Server errror: {str(exc)}")
