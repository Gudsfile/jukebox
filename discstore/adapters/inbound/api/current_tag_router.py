from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import ValidationError

from discstore.adapters.inbound.api.models import (
    CurrentTagDiscOutput,
    CurrentTagStatusOutput,
    DiscInput,
    DiscOutput,
    DiscPatchInput,
)
from discstore.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
from discstore.domain.use_cases.add_disc import AddDisc
from discstore.domain.use_cases.edit_disc import EditDisc
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus
from discstore.domain.use_cases.get_disc import GetDisc
from discstore.domain.use_cases.remove_disc import RemoveDisc


def build_current_tag_router(
    get_current_tag_status: GetCurrentTagStatus,
    add_disc: AddDisc,
    edit_disc: EditDisc,
    get_disc: GetDisc,
    remove_disc: RemoveDisc,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["current-tag"])

    def read_current_tag_status() -> Optional[CurrentTagStatus]:
        return get_current_tag_status.execute()

    def ensure_expected_tag_id_matches(
        expected_tag_id: Optional[str], current_tag_status: Optional[CurrentTagStatus]
    ) -> None:
        if expected_tag_id is None:
            return

        actual_tag_id = None if current_tag_status is None else current_tag_status.tag_id
        if actual_tag_id != expected_tag_id:
            raise HTTPException(
                status_code=409,
                detail=f"Current tag changed: expected_tag_id='{expected_tag_id}', actual_tag_id={repr(actual_tag_id)}",
            )

    def build_current_tag_disc_output(tag_id: str, disc: Disc) -> CurrentTagDiscOutput:
        return CurrentTagDiscOutput(tag_id=tag_id, disc=DiscOutput(**disc.model_dump()))

    @router.get(
        "/current-tag",
        response_model=CurrentTagStatusOutput,
        responses={204: {"description": "No current tag"}},
        summary="Get the current NFC tag status",
    )
    def get_current_tag() -> Any:
        current_tag_status = read_current_tag_status()
        if current_tag_status is None:
            return Response(status_code=204)

        return CurrentTagStatusOutput(**current_tag_status.model_dump())

    @router.get(
        "/current-tag/disc",
        response_model=CurrentTagDiscOutput,
        responses={204: {"description": "No current tag"}, 404: {"description": "Current tag disc not found"}},
        summary="Get the current tag disc",
    )
    def get_current_tag_disc() -> Any:
        current_tag_status = read_current_tag_status()
        if current_tag_status is None:
            return Response(status_code=204)

        if not current_tag_status.known_in_library:
            raise HTTPException(status_code=404, detail=f"Tag does not exist: tag_id='{current_tag_status.tag_id}'")

        return build_current_tag_disc_output(current_tag_status.tag_id, get_disc.execute(current_tag_status.tag_id))

    @router.post(
        "/current-tag/disc",
        response_model=CurrentTagDiscOutput,
        status_code=201,
        responses={204: {"description": "No current tag"}, 409: {"description": "Current tag changed or disc exists"}},
        summary="Create a disc for the current tag",
    )
    def create_current_tag_disc(
        disc: DiscInput,
        expected_tag_id: Optional[str] = None,
    ) -> Any:
        current_tag_status = read_current_tag_status()
        ensure_expected_tag_id_matches(expected_tag_id, current_tag_status)
        if current_tag_status is None:
            return Response(status_code=204)

        try:
            new_disc = Disc(**disc.model_dump())
            created_disc = add_disc.execute(current_tag_status.tag_id, new_disc)
            return build_current_tag_disc_output(current_tag_status.tag_id, created_disc)
        except ValueError as value_err:
            raise HTTPException(status_code=409, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.patch(
        "/current-tag/disc",
        response_model=CurrentTagDiscOutput,
        responses={
            204: {"description": "No current tag"},
            404: {"description": "Current tag disc not found"},
            409: {"description": "Current tag changed"},
        },
        summary="Update the current tag disc",
    )
    def update_current_tag_disc(
        disc_patch: DiscPatchInput,
        expected_tag_id: Optional[str] = None,
    ) -> Any:
        current_tag_status = read_current_tag_status()
        ensure_expected_tag_id_matches(expected_tag_id, current_tag_status)
        if current_tag_status is None:
            return Response(status_code=204)

        try:
            metadata = None
            if disc_patch.metadata is not None:
                metadata = DiscMetadata(**disc_patch.metadata.model_dump(exclude_unset=True))

            option = None
            if disc_patch.option is not None:
                option = DiscOption(**disc_patch.option.model_dump(exclude_unset=True))

            updated_disc = edit_disc.execute(current_tag_status.tag_id, disc_patch.uri, metadata, option)
            return build_current_tag_disc_output(current_tag_status.tag_id, updated_disc)
        except ValidationError as err:
            raise HTTPException(status_code=422, detail=err.errors())
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    @router.delete(
        "/current-tag/disc",
        status_code=204,
        responses={
            204: {"description": "No current tag or disc deleted"},
            404: {"description": "Current tag disc not found"},
            409: {"description": "Current tag changed"},
        },
        summary="Delete the current tag disc",
    )
    def delete_current_tag_disc(expected_tag_id: Optional[str] = None) -> Response:
        current_tag_status = read_current_tag_status()
        ensure_expected_tag_id_matches(expected_tag_id, current_tag_status)
        if current_tag_status is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        try:
            remove_disc.execute(current_tag_status.tag_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        except ValueError as value_err:
            raise HTTPException(status_code=404, detail=str(value_err))
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Server error: {str(err)}")

    return router
