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
    delete_button = components[1]

    assert form.type == "ModelForm"
    assert form.submit_url == "/api/ui/discs/tag-123"
    assert form.initial == {
        "tag": "tag-123",
        "uri": "/music/song.mp3",
        "artist": "Artist",
        "album": "Album",
        "track": "Track",
        "playlist": None,
        "shuffle": True,
    }
    assert delete_button.text == "🗑️ Delete this disc"
    assert delete_button.on_click.url == "/discs/tag-123/delete"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_edit_disc_form_components_prefill_playlist_disc():
    from jukebox.domain.entities import Disc, DiscMetadata, DiscOption

    page_builder = build_library_page_builder()
    page_builder.get_disc.execute.return_value = Disc(
        uri="spotify:playlist:abc",
        metadata=DiscMetadata(playlist="My Mix", artist="Spotify"),
        option=DiscOption(shuffle=True),
    )

    components = page_builder.build_edit_disc_form_components("tag-123")
    form = components[0]

    assert form.initial == {
        "tag": "tag-123",
        "uri": "spotify:playlist:abc",
        "artist": "Spotify",
        "album": None,
        "track": None,
        "playlist": "My Mix",
        "shuffle": True,
    }


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_disc_table_shows_type_and_title_columns_for_album(walk_components):
    from jukebox.adapters.inbound.admin.ui_pages.library import DiscTable

    page_builder = build_library_page_builder()
    components = page_builder.build_disc_library_components(
        [DiscTable(tag="tag-123", uri="/music/song.mp3", artist="abcd", album="efgh ijkl", shuffle=False)]
    )
    all_texts = [c.text for c in walk_components(components) if hasattr(c, "text") and c.text]

    assert "💿 Album" in all_texts
    assert "abcd — efgh ijkl" in all_texts
    assert "Artist" not in all_texts
    assert "Album" not in all_texts


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_disc_table_shows_type_and_title_columns_for_playlist(walk_components):
    from jukebox.adapters.inbound.admin.ui_pages.library import DiscTable

    page_builder = build_library_page_builder()
    components = page_builder.build_disc_library_components(
        [DiscTable(tag="tag-123", uri="spotify:playlist:abc", playlist="My Mix", artist="Spotify", shuffle=False)]
    )
    all_texts = [c.text for c in walk_components(components) if hasattr(c, "text") and c.text]

    assert "🎧 Playlist" in all_texts
    assert "My Mix (Spotify)" in all_texts


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_delete_disc_form_components_render_confirmation_and_actions(walk_components):
    page_builder = build_library_page_builder()

    page = page_builder.build_form_page_components(
        "Delete disc tag-123",
        page_builder.build_delete_disc_form_components("tag-123"),
    )[0]
    all_components = list(walk_components(page.components))

    assert page.components[0].text == "Delete disc tag-123"
    assert page.components[1].text == 'Are you sure you want to delete the disc with tag "tag-123"?'
    confirm_deletion_form = next(component for component in all_components if component.type == "Form")
    cancel_deletion_button = next(
        component for component in all_components if component.type == "Button" and component.text == "Cancel"
    )
    assert confirm_deletion_form.submit_url == "/api/ui/discs/tag-123/delete"
    assert cancel_deletion_button.on_click.type == "back"


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
    first_chunk = await anext(stream)

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


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_index_page_renders_server_load_and_navigation(walk_components):
    from jukebox.domain.entities import Disc, DiscMetadata, DiscOption

    page_builder = build_library_page_builder()
    page_builder.list_discs.execute.return_value = {
        "tag-123": Disc(
            uri="/music/song.mp3",
            metadata=DiscMetadata(artist="Artist", album="Album", track="Track"),
            option=DiscOption(shuffle=True),
        )
    }

    page = page_builder.build_index_page_components()[0]
    all_components = list(walk_components(page.components))

    server_load = next(component for component in all_components if component.type == "ServerLoad")
    add_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "➕ Add a new disc"
    )
    sonos_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "🔊 Sonos Speakers"
    )
    settings_button = next(
        component for component in all_components if component.type == "Button" and component.text == "⚙️ Settings"
    )
    edit_button = next(
        component
        for component in all_components
        if component.type == "Button" and component.text == "Edit ✏️" and component.on_click is not None
    )

    assert server_load.path == "/current-tag-banner/events"
    assert server_load.sse is True
    assert add_button.on_click.url == "/discs/new"
    assert sonos_button.on_click.url == "/sonos"
    assert settings_button.on_click.url == "/settings"
    assert edit_button.on_click.url == "/discs/tag-123/edit"
    assert any(component.type == "Paragraph" and component.text == "URI / Path" for component in all_components)
