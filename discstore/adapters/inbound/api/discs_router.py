from typing import Dict

from fastapi import APIRouter, HTTPException, Response, status

from discstore.adapters.inbound.api.models import DiscInput, DiscOutput, DiscPatchInput
from discstore.domain.entities import Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.list_discs import ListDiscs
from discstore.domain.use_cases.remove_disc import RemoveDisc


def build_discs_router(
    add_disc: AddDisc,
    list_discs: ListDiscs,
    remove_disc: RemoveDisc,
    edit_disc: EditDisc,
    get_disc: GetDisc,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["discs"])

    @router.get("/discs", response_model=Dict[str, DiscOutput], summary="List discs")
    def list_discs_route() -> Dict[str, Disc]:
        return list_discs.execute()

    @router.get("/discs/{tag_id}", response_model=DiscOutput, summary="Get a disc")
    def get_disc_route(tag_id: str) -> Disc:
        try:
            return get_disc.execute(tag_id)
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.post("/discs/{tag_id}", response_model=DiscOutput, status_code=201, summary="Create a disc")
    def create_disc_route(tag_id: str, disc: DiscInput) -> Disc:
        try:
            new_disc = Disc(**disc.model_dump())
            return add_disc.execute(tag_id, new_disc)
        except ValueError as value_err:
            raise HTTPException(status_code=409, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.patch("/discs/{tag_id}", response_model=DiscOutput, summary="Update a disc")
    def update_disc_route(tag_id: str, disc_patch: DiscPatchInput) -> Disc:
        try:
            metadata = None
            if disc_patch.metadata is not None:
                metadata = DiscMetadata(**disc_patch.metadata.model_dump(exclude_unset=True, exclude_none=True))

            option = None
            if disc_patch.option is not None:
                option = DiscOption(**disc_patch.option.model_dump(exclude_unset=True, exclude_none=True))

            return edit_disc.execute(tag_id, disc_patch.uri, metadata, option)
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.delete("/discs/{tag_id}", status_code=204, summary="Delete a disc")
    def remove_disc_route(tag_id: str) -> Response:
        try:
            remove_disc.execute(tag_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    return router
