from importlib import util
from unittest.mock import MagicMock, create_autospec

import pytest

FASTUI_INSTALLED = util.find_spec("fastui") is not None


def build_speaker(uid, name, host, household_id):
    from jukebox.sonos.discovery import DiscoveredSonosSpeaker

    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def build_sonos_page_builder():
    from jukebox.adapters.inbound.admin.ui_pages.sonos import SonosUIPageBuilder
    from jukebox.sonos.service import InspectedSelectedSonosGroup, SonosService

    settings_service = MagicMock()
    sonos_service = create_autospec(SonosService)
    available_speakers = [
        build_speaker(uid="speaker-1", name="Kitchen", host="192.168.1.30", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-1"),
    ]
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "household_id": "household-1",
                        "coordinator_uid": "speaker-2",
                        "members": [
                            {"uid": "speaker-1"},
                            {"uid": "speaker-2"},
                        ],
                    }
                }
            }
        },
    }
    sonos_service.list_network_speakers.return_value = available_speakers
    sonos_service.inspect_selected_group.return_value = InspectedSelectedSonosGroup(
        coordinator=available_speakers[1],
        resolved_members=list(available_speakers),
        missing_member_uids=[],
        error_message=None,
    )

    return SonosUIPageBuilder(settings_service=settings_service, sonos_service=sonos_service)


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_sonos_page_renders_saved_selection_and_discovered_speakers(walk_components):
    page_builder = build_sonos_page_builder()

    page = page_builder.build_sonos_page_components(toast="toast-sonos-success", toast_message="Sonos settings saved.")
    all_components = list(walk_components(page[0].components))

    assert any(component.type == "Heading" and component.text == "Sonos Speakers" for component in all_components)
    assert any(component.type == "Heading" and component.text == "Saved selection" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Status: Available" for component in all_components)
    assert any(
        component.type == "Paragraph" and component.text == "Coordinator: Living Room [speaker-2]"
        for component in all_components
    )
    assert any(
        component.type == "Paragraph" and component.text == "Members: Kitchen [speaker-1], Living Room [speaker-2]"
        for component in all_components
    )
    assert any(component.type == "Heading" and component.text == "Discovered speakers" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Kitchen" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Living Room" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Coordinator" for component in all_components)
    assert any(component.type == "Paragraph" and component.text == "Selected" for component in all_components)
    assert page[1].event.name == "toast-sonos-success"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_sonos_edit_page_renders_speaker_and_coordinator_selects(walk_components):
    page_builder = build_sonos_page_builder()

    page = page_builder.build_sonos_edit_page_components()[0]
    form = next(component for component in walk_components(page.components) if component.type == "Form")
    speakers_field = form.form_fields[0]
    coordinator_field = form.form_fields[1]

    assert page.components[0].text == "Edit Sonos Selection"
    assert not any(
        component.type == "Heading" and component.text == "Saved selection"
        for component in walk_components(page.components)
    )
    assert any(
        component.type == "Paragraph" and component.text == "Current saved selection"
        for component in walk_components(page.components)
    )
    assert any(
        component.type == "Paragraph" and component.text == "Coordinator: Living Room [speaker-2]"
        for component in walk_components(page.components)
    )
    assert speakers_field.type == "FormFieldSelect"
    assert speakers_field.name == "uids"
    assert speakers_field.multiple is True
    assert speakers_field.initial == ["speaker-1", "speaker-2"]
    assert speakers_field.options == [
        {"value": "speaker-1", "label": "Kitchen (192.168.1.30)"},
        {"value": "speaker-2", "label": "Living Room (192.168.1.31)"},
    ]
    assert coordinator_field.type == "FormFieldSelect"
    assert coordinator_field.name == "coordinator_uid"
    assert coordinator_field.initial == "speaker-2"
    assert form.submit_url == "/api/ui/sonos/edit"
    assert form.method == "POST"


@pytest.mark.skipif(not FASTUI_INSTALLED, reason="FastUI dependencies are not installed")
def test_sonos_edit_page_renders_error_banner_and_preserves_submitted_values(walk_components):
    page_builder = build_sonos_page_builder()

    error_message = "Selected Sonos coordinator must be one of the selected speakers: Living Room [speaker-2]"
    page = page_builder.build_sonos_edit_page_components(
        error_message=error_message,
        field_errors={"coordinator_uid": error_message},
        submitted_uids=["speaker-1"],
        submitted_coordinator_uid="speaker-2",
    )[0]
    all_components = list(walk_components(page.components))
    form = next(component for component in all_components if component.type == "Form")
    speakers_field = form.form_fields[0]
    coordinator_field = form.form_fields[1]

    assert any(
        component.type == "Paragraph" and component.text == "Selection not saved" for component in all_components
    )
    assert any(component.type == "Paragraph" and component.text == error_message for component in all_components)
    assert speakers_field.initial == ["speaker-1"]
    assert speakers_field.error is None
    assert coordinator_field.initial == "speaker-2"
    assert coordinator_field.error == error_message
