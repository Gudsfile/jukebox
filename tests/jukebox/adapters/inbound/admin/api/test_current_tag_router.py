import importlib.util
from unittest.mock import MagicMock, create_autospec

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.current_tag_router import build_current_tag_router
    from jukebox.adapters.inbound.admin.api.models import (
        DiscInput,
        DiscPatchInput,
        DiscPatchMetadataInput,
        DiscPatchOptionInput,
    )
    from jukebox.domain.entities import CurrentTagStatus, Disc, DiscMetadata, DiscOption
    from jukebox.domain.use_cases.library.get_current_tag_status import GetCurrentTagStatus


def build_router(
    *,
    get_current_tag_status=None,
    add_disc=None,
    edit_disc=None,
    get_disc=None,
    remove_disc=None,
):
    return build_current_tag_router(
        get_current_tag_status=get_current_tag_status if get_current_tag_status is not None else MagicMock(),
        add_disc=add_disc if add_disc is not None else MagicMock(),
        edit_disc=edit_disc if edit_disc is not None else MagicMock(),
        get_disc=get_disc if get_disc is not None else MagicMock(),
        remove_disc=remove_disc if remove_disc is not None else MagicMock(),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("known_in_library", [True, False])
def test_get_current_tag_returns_current_tag_payload(get_route, known_in_library):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=known_in_library)
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag", "GET")

    response = route.endpoint()

    assert route.response_model is not None
    assert route.response_model.__name__ == "CurrentTagStatusOutput"
    assert response.model_dump() == {"tag_id": "tag-123", "known_in_library": known_in_library}
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_returns_no_content_when_absent(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag", "GET")

    response = route.endpoint()

    assert 204 in route.responses
    assert response.status_code == 204
    assert response.body == b""
    get_current_tag_status.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_tag_and_disc_payload(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    get_disc = MagicMock()
    get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    router = build_router(get_current_tag_status=get_current_tag_status, get_disc=get_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "GET")

    response = route.endpoint()

    assert route.response_model is not None
    assert route.response_model.__name__ == "CurrentTagDiscOutput"
    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": {
            "uri": "/music/song.mp3",
            "metadata": {"artist": "Artist", "album": "Album", "track": "Track", "playlist": None},
            "option": {"shuffle": True, "is_test": False},
        },
    }
    get_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_no_content_when_absent(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag/disc", "GET")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_current_tag_disc_returns_404_when_current_tag_is_unknown(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag/disc", "GET")

    with pytest.raises(HTTPException) as err:
        route.endpoint()

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_created_disc_payload(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    add_disc = MagicMock()
    request = DiscInput(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    add_disc.execute.return_value = Disc(**request.model_dump())
    router = build_router(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "POST")

    response = route.endpoint(request)

    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": request.model_dump(),
    }
    add_disc.execute.assert_called_once_with("tag-123", Disc(**request.model_dump()))


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_no_content_when_absent(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    add_disc = MagicMock()
    router = build_router(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "POST")

    response = route.endpoint(DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()))

    assert response.status_code == 204
    assert response.body == b""
    add_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_current_tag_disc_returns_409_when_tag_exists(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    add_disc = MagicMock()
    add_disc.execute.side_effect = ValueError("Already existing tag: tag_id='tag-123'")
    router = build_router(get_current_tag_status=get_current_tag_status, add_disc=add_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(artist="Artist"), option=DiscOption()))

    assert err.value.status_code == 409
    assert err.value.detail == "Already existing tag: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_partially_updates_existing_disc(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    edit_disc = MagicMock()
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=False),
    )
    router = build_router(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(
        DiscPatchInput(
            metadata=DiscPatchMetadataInput(track="Updated Track"),
            option=DiscPatchOptionInput(shuffle=False),
        )
    )

    assert response.model_dump() == {
        "tag_id": "tag-123",
        "disc": {
            "uri": "/music/song.mp3",
            "metadata": {"artist": "Artist", "album": "Album", "track": "Updated Track", "playlist": None},
            "option": {"shuffle": False, "is_test": False},
        },
    }
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(track="Updated Track"),
        DiscOption(shuffle=False),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_no_content_when_absent(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    edit_disc = MagicMock()
    router = build_router(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(DiscPatchInput(uri="/music/new-song.mp3"))

    assert response.status_code == 204
    assert response.body == b""
    edit_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_404_when_missing(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="missing", known_in_library=False)
    edit_disc = MagicMock()
    edit_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    router = build_router(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscPatchInput(uri="/music/new-song.mp3"))

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_returns_422_when_null_assigned_to_non_nullable_option_field(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag/disc", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint(DiscPatchInput(option=DiscPatchOptionInput(shuffle=None)))

    assert err.value.status_code == 422


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_current_tag_disc_forwards_null_metadata_to_edit_disc(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    edit_disc = MagicMock()
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(album="Album", track="Track"),
        option=DiscOption(),
    )
    router = build_router(get_current_tag_status=get_current_tag_status, edit_disc=edit_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "PATCH")

    response = route.endpoint(DiscPatchInput(metadata=DiscPatchMetadataInput(artist=None)))

    assert response.tag_id == "tag-123"
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(artist=None),
        None,
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_current_tag_disc_returns_no_content(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    remove_disc = MagicMock()
    router = build_router(get_current_tag_status=get_current_tag_status, remove_disc=remove_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "DELETE")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_current_tag_disc_returns_no_content_when_absent(get_route):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = None
    remove_disc = MagicMock()
    router = build_router(get_current_tag_status=get_current_tag_status, remove_disc=remove_disc)
    route = get_route(router, "/api/v1/current-tag/disc", "DELETE")

    response = route.endpoint()

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_not_called()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_current_tag_disc_mutations_return_409_when_expected_tag_id_mismatches(get_route, method):
    get_current_tag_status = create_autospec(GetCurrentTagStatus, instance=True, spec_set=True)
    get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="other-tag", known_in_library=True)
    router = build_router(get_current_tag_status=get_current_tag_status)
    route = get_route(router, "/api/v1/current-tag/disc", method)

    if method == "POST":
        call_args = (DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(), option=DiscOption()), "tag-123")
    elif method == "PATCH":
        call_args = (DiscPatchInput(uri="/music/song.mp3"), "tag-123")
    else:
        call_args = ("tag-123",)

    with pytest.raises(HTTPException) as err:
        route.endpoint(*call_args)

    assert err.value.status_code == 409
    assert err.value.detail == "Current tag changed: expected_tag_id='tag-123', actual_tag_id='other-tag'"
