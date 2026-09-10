import importlib.util

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from jukebox.adapters.inbound.admin.api.models import DiscOutput
    from jukebox.domain.entities import DiscMetadata, DiscOption


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_disc_output_serializes_display_type_and_title():
    disc = DiscOutput(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", track="Track"),
        option=DiscOption(),
    )

    dumped = disc.model_dump()

    assert dumped["display_type"] == "\U0001f3b5 Track"
    assert dumped["display_title"] == "Artist — Track"


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_disc_output_display_fields_follow_metadata_precedence():
    playlist_disc = DiscOutput(
        uri="/music/mix.mp3",
        metadata=DiscMetadata(artist="DJ", playlist="Chill Mix"),
        option=DiscOption(),
    )

    dumped = playlist_disc.model_dump()

    assert dumped["display_type"] == "\U0001f3a7 Playlist"
    assert dumped["display_title"] == "Chill Mix (DJ)"
