from typing import Any

from fastapi import APIRouter, Response

from discstore.adapters.inbound.api.models import CurrentTagStatusOutput
from discstore.domain.use_cases.get_current_tag_status import GetCurrentTagStatus


def build_current_tag_router(get_current_tag_status: GetCurrentTagStatus) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["current-tag"])

    @router.get(
        "/current-tag",
        response_model=CurrentTagStatusOutput,
        responses={204: {"description": "No current tag"}},
        summary="Get the current NFC tag status",
    )
    def get_current_tag() -> Any:
        current_tag_status = get_current_tag_status.execute()
        if current_tag_status is None:
            return Response(status_code=204)

        return CurrentTagStatusOutput(**current_tag_status.model_dump())

    return router
