from typing import Dict

from fastapi import APIRouter, HTTPException

from discstore.adapters.inbound.api.models import DiscInput, DiscOutput
from discstore.domain.entities import Disc
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


def build_discs_router(
    add_disc: AddDisc,
    list_discs: ListDiscs,
    remove_disc: RemoveDisc,
    edit_disc: EditDisc,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["discs"])

    @router.get("/discs", response_model=Dict[str, DiscOutput], summary="List discs")
    def list_discs_route() -> Dict[str, Disc]:
        return list_discs.execute()

    @router.post("/disc", status_code=201, summary="Create or update a disc")
    def add_or_edit_disc(tag_id: str, disc: DiscInput) -> Dict[str, str]:
        try:
            self_disc = Disc(**disc.model_dump())
            add_disc.execute(tag_id, self_disc)
            return {"message": "Disc added"}
        except ValueError:
            new_disc = Disc(**disc.model_dump())
            edit_disc.execute(tag_id, new_disc.uri, new_disc.metadata, new_disc.option)
            return {"message": "Disc edited"}
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.delete("/disc", status_code=200, summary="Delete a disc")
    def remove_disc_route(tag_id: str) -> Dict[str, str]:
        try:
            remove_disc.execute(tag_id)
            return {"message": "Disc removed"}
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    return router
