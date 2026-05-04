from importlib import util
from unittest.mock import AsyncMock, MagicMock

import pytest

FASTUI_INSTALLED = util.find_spec("fastui") is not None


def build_library_page_builder():
    from jukebox.adapters.inbound.admin.ui_pages.library import LibraryUIPageBuilder

    list_discs = MagicMock()
    get_disc = MagicMock()
    get_current_tag_status = MagicMock()
    list_discs.execute.return_value = {}
    get_current_tag_status.execute.return_value = None

    return LibraryUIPageBuilder(
        list_discs=list_discs,
        get_disc=get_disc,
        get_current_tag_status=get_current_tag_status,
    )


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_disc_library_components_render_empty_and_editable_states(walk_components):
    from jukebox.adapters.inbound.admin.ui_pages.library import DiscTable

    page_builder = build_library_page_builder()
    empty_components = page_builder.build_disc_library_components([])
    populated_components = page_builder.build_disc_library_components(
        [
            DiscTable(
                tag="tag-123",
                uri="/music/song.mp3",
                artist="Artist",
                album="Album",
                track="Track",
                shuffle=True,
            )
        ]
    )

    assert empty_components[0].type == "Paragraph"
    assert empty_components[0].text == "No disc found"
    edit_button = next(
        component
        for component in walk_components(populated_components)
        if component.type == "Button" and component.text == "Edit ✏️" and component.on_click is not None
    )
    assert edit_button.on_click.url == "/discs/tag-123/edit"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_current_tag_banner_for_unknown_disc_offers_add_cta(walk_components):
    from jukebox.domain.entities import CurrentTagStatus

    page_builder = build_library_page_builder()

    components = page_builder.build_current_tag_banner_components(
        CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    )
    all_components = list(walk_components(components))
    heading = next(component for component in all_components if component.type == "Heading")
    button = next(component for component in all_components if component.type == "Button")

    assert heading.text == "Unknown disc on reader"
    assert button.text == "Add this disc"
    assert button.on_click.url == "/discs/new?prefill=current"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_current_tag_banner_for_known_disc_is_informational_only(walk_components):
    from jukebox.domain.entities import CurrentTagStatus

    page_builder = build_library_page_builder()

    components = page_builder.build_current_tag_banner_components(
        CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    )
    all_components = list(walk_components(components))
    button = next(component for component in all_components if component.type == "Button")

    assert any(component.type == "Heading" and component.text == "Known disc on reader" for component in all_components)
    assert button.text == "Edit this disc"
    assert button.on_click.url == "/discs/tag-123/edit"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_new_disc_form_components_render_blank_add_form():
    page_builder = build_library_page_builder()

    components = page_builder.build_new_disc_form_components(prefill_current=False)
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs"
    assert form.initial is None


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_new_disc_form_components_can_prefill_current_tag():
    from jukebox.domain.entities import CurrentTagStatus

    page_builder = build_library_page_builder()
    page_builder.get_current_tag_status.execute.return_value = CurrentTagStatus(
        tag_id="tag-123", known_in_library=False
    )

    components = page_builder.build_new_disc_form_components(prefill_current=True)
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs"
    assert form.initial == {"tag": "tag-123", "shuffle": False}


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_edit_disc_form_components_prefill_existing_disc():
    from jukebox.domain.entities import Disc, DiscMetadata, DiscOption

    page_builder = build_library_page_builder()
    page_builder.get_disc.execute.return_value = Disc(
        uri="/music/song.mp3",
        metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
        option=DiscOption(shuffle=True),
    )

    components = page_builder.build_edit_disc_form_components("tag-123")
    form = components[0]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs/tag-123"
    assert form.initial == {
        "tag": "tag-123",
        "uri": "/music/song.mp3",
        "artist": "Artist",
        "album": "Album",
        "track": "Track",
        "shuffle": True,
    }


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_disc_form_helpers_return_errors_for_invalid_current_tag_state_or_missing_edit_target():
    from jukebox.domain.entities import CurrentTagStatus

    page_builder = build_library_page_builder()

    page_builder.get_current_tag_status.execute.return_value = None
    no_tag_components = page_builder.build_new_disc_form_components(prefill_current=True)
    page_builder.get_current_tag_status.execute.return_value = CurrentTagStatus(tag_id="tag-123", known_in_library=True)
    known_tag_components = page_builder.build_new_disc_form_components(prefill_current=True)
    missing_tag_components = page_builder.build_edit_disc_form_components("")
    page_builder.get_disc.execute.side_effect = ValueError("Missing disc")
    missing_disc_components = page_builder.build_edit_disc_form_components("tag-123")

    assert no_tag_components[0].type == "Error"
    assert known_tag_components[0].type == "Error"
    assert missing_tag_components[0].type == "Error"
    assert missing_disc_components[0].type == "Error"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_form_page_components_include_back_link_and_form(walk_components):
    page_builder = build_library_page_builder()
    components = page_builder.build_form_page_components(
        title="Add disc",
        form_components=page_builder.build_new_disc_form_components(prefill_current=False),
    )

    page_components = list(walk_components(components))
    assert components[0].type == "Page"
    assert any(component.type == "Heading" and component.text == "Add disc" for component in page_components)
    assert any(component.type == "ModelForm" for component in page_components)
    assert any(component.type == "Link" and component.on_click.url == "/" for component in page_components)


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
@pytest.mark.anyio
async def test_current_tag_banner_event_stream_emits_serialized_updates():
    from jukebox.domain.entities import CurrentTagStatus

    page_builder = build_library_page_builder()
    page_builder.get_current_tag_status.execute.side_effect = [
        CurrentTagStatus(tag_id="tag-123", known_in_library=False)
    ]
    request = MagicMock()
    request.is_disconnected = AsyncMock(side_effect=[False])

    stream = page_builder.current_tag_banner_event_stream(request, poll_interval_seconds=0)
    # Avoid the Python 3.10+ `anext` builtin because this repo still supports Python 3.9.
    first_chunk = await stream.__anext__()

    assert first_chunk.decode("utf-8").startswith("data: [")
    assert "Unknown disc on reader" in first_chunk.decode("utf-8")


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_index_page_shows_remove_toast(walk_components):
    page_builder = build_library_page_builder()
    components = page_builder.build_index_page_components(toast="toast-remove-disc-success")
    all_components = list(walk_components(components))

    remove_toast = next(
        component for component in all_components if component.type == "Toast" and "removed" in str(component.body)
    )
    assert remove_toast.open_trigger.name == "toast-remove-disc-success"
