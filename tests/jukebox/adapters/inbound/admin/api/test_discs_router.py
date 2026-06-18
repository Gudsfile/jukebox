import importlib.util
from unittest.mock import MagicMock, create_autospec

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from fastapi import HTTPException

    from jukebox.adapters.inbound.admin.api.discs_router import build_discs_router
    from jukebox.adapters.inbound.admin.api.models import (
        DiscInput,
        DiscOutput,
        DiscPatchInput,
        DiscPatchMetadataInput,
        DiscPatchOptionInput,
    )
    from jukebox.domain.entities import Disc, DiscMetadata, DiscOption
    from jukebox.domain.use_cases.library.add_disc import AddDisc
    from jukebox.domain.use_cases.library.edit_disc import EditDisc
    from jukebox.domain.use_cases.library.get_disc import GetDisc
    from jukebox.domain.use_cases.library.list_discs import ListDiscs
    from jukebox.domain.use_cases.library.remove_disc import RemoveDisc


def build_router(
    *,
    add_disc=None,
    list_discs=None,
    remove_disc=None,
    edit_disc=None,
    get_disc=None,
):
    return build_discs_router(
        add_disc=add_disc if add_disc is not None else MagicMock(),
        list_discs=list_discs if list_discs is not None else MagicMock(),
        remove_disc=remove_disc if remove_disc is not None else MagicMock(),
        edit_disc=edit_disc if edit_disc is not None else MagicMock(),
        get_disc=get_disc if get_disc is not None else MagicMock(),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_list_discs_returns_disc_list(get_route):
    list_discs = create_autospec(ListDiscs, instance=True)
    list_discs.execute.return_value = {
        "tag-1": Disc(uri="/music/song1.mp3", metadata=DiscMetadata(artist="Artist 1"), option=DiscOption()),
        "tag-2": Disc(uri="/music/song2.mp3", metadata=DiscMetadata(artist="Artist 2"), option=DiscOption()),
    }
    router = build_router(list_discs=list_discs)
    route = get_route(router, "/api/v1/discs", "GET")

    response = route.endpoint()

    assert route.response_model == dict[str, DiscOutput]
    assert response == list_discs.execute.return_value
    list_discs.execute.assert_called_once_with()


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_disc_returns_disc_payload(get_route):
    get_disc = create_autospec(GetDisc, instance=True)
    get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    router = build_router(get_disc=get_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "GET")

    response = route.endpoint("tag-123")

    assert route.response_model is not None
    assert route.response_model.__name__ == "DiscOutput"
    assert response.model_dump() == {
        "uri": "/music/song.mp3",
        "metadata": {"artist": "Artist", "album": "Album", "track": "Track", "playlist": None},
        "option": {"shuffle": True, "is_test": False},
    }
    get_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_disc_returns_404_when_missing(get_route):
    get_disc = create_autospec(GetDisc, instance=True)
    get_disc.execute.side_effect = ValueError("Tag not found: tag_id='missing'")
    router = build_router(get_disc=get_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "GET")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing")

    assert err.value.status_code == 404
    assert err.value.detail == "Tag not found: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_disc_returns_created_disc_payload(get_route):
    add_disc = create_autospec(AddDisc, instance=True)
    add_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )
    router = build_router(add_disc=add_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "POST")
    request = DiscInput(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )

    response = route.endpoint("tag-123", request)

    assert response.model_dump() == request.model_dump()
    add_disc.execute.assert_called_once_with("tag-123", Disc(**request.model_dump()))


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_create_disc_returns_409_when_tag_exists(get_route):
    add_disc = create_autospec(AddDisc, instance=True)
    add_disc.execute.side_effect = ValueError("Already existing tag: tag_id='tag-123'")
    router = build_router(add_disc=add_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "POST")

    with pytest.raises(HTTPException) as err:
        route.endpoint(
            "tag-123",
            DiscInput(uri="/music/song.mp3", metadata=DiscMetadata(artist="Artist"), option=DiscOption()),
        )

    assert err.value.status_code == 409
    assert err.value.detail == "Already existing tag: tag_id='tag-123'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_partially_updates_existing_disc(get_route):
    edit_disc = create_autospec(EditDisc, instance=True)
    edit_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Updated Track"),
        option=DiscOption(shuffle=False),
    )
    router = build_router(edit_disc=edit_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "PATCH")

    response = route.endpoint(
        "tag-123",
        DiscPatchInput(
            metadata=DiscPatchMetadataInput(track="Updated Track"),
            option=DiscPatchOptionInput(shuffle=False),
        ),
    )

    assert response.model_dump() == {
        "uri": "/music/song.mp3",
        "metadata": {"artist": "Artist", "album": "Album", "track": "Updated Track", "playlist": None},
        "option": {"shuffle": False, "is_test": False},
    }
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(track="Updated Track"),
        DiscOption(shuffle=False),
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_returns_422_when_null_assigned_to_non_nullable_option_field(get_route):
    router = build_router()
    route = get_route(router, "/api/v1/discs/{tag_id}", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint("tag-123", DiscPatchInput(option=DiscPatchOptionInput(shuffle=None)))

    assert err.value.status_code == 422


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_returns_404_when_missing(get_route):
    edit_disc = create_autospec(EditDisc, instance=True)
    edit_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    router = build_router(edit_disc=edit_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "PATCH")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing", DiscPatchInput(uri="/music/new-song.mp3"))

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_patch_disc_forwards_null_metadata_to_edit_disc(get_route):
    edit_disc = create_autospec(EditDisc, instance=True)
    edit_disc.execute.return_value = "the_value_returned_by_the_EditDisc_use_case"
    router = build_router(edit_disc=edit_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "PATCH")

    response = route.endpoint("tag-123", DiscPatchInput(metadata=DiscPatchMetadataInput(artist=None)))

    assert response == "the_value_returned_by_the_EditDisc_use_case"
    edit_disc.execute.assert_called_once_with(
        "tag-123",
        None,
        DiscMetadata(artist=None),
        None,
    )


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_disc_returns_no_content(get_route):
    remove_disc = create_autospec(RemoveDisc, instance=True)
    router = build_router(remove_disc=remove_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "DELETE")

    response = route.endpoint("tag-123")

    assert response.status_code == 204
    assert response.body == b""
    remove_disc.execute.assert_called_once_with("tag-123")


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_delete_disc_returns_404_when_missing(get_route):
    remove_disc = create_autospec(RemoveDisc, instance=True)
    remove_disc.execute.side_effect = ValueError("Tag does not exist: tag_id='missing'")
    router = build_router(remove_disc=remove_disc)
    route = get_route(router, "/api/v1/discs/{tag_id}", "DELETE")

    with pytest.raises(HTTPException) as err:
        route.endpoint("missing")

    assert err.value.status_code == 404
    assert err.value.detail == "Tag does not exist: tag_id='missing'"
