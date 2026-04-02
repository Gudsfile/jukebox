from unittest.mock import MagicMock

import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import (
    GetSonosSelectionStatus,
    PlanSonosSelection,
    SaveSelectedSonosGroupResult,
    SaveSonosSelection,
)


def build_speaker(uid="speaker-1", name="Kitchen", host="192.168.1.30", household_id="household-1"):
    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def test_plan_sonos_selection_resolves_single_requested_uid():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=["speaker-1"])

    assert plan.status == "resolved"
    assert plan.selected_uid == "speaker-1"


def test_save_sonos_selection_persists_one_member_selected_group_and_player_type():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult(
        message="Settings saved. Changes take effect after restart."
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    result = SaveSonosSelection(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute("speaker-1")

    assert result.speaker.uid == "speaker-1"
    assert result.selected_group == SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )
    selected_group_repository.save_selected_group.assert_called_once_with(
        SelectedSonosGroupSettings(
            coordinator_uid="speaker-1",
            members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
        )
    )


def test_plan_sonos_selection_rejects_unknown_uid():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=["speaker-9"])

    assert plan.status == "invalid_request"
    assert plan.error_message == "Selected Sonos speaker is not currently discoverable: speaker-9"


def test_save_sonos_selection_rejects_unknown_uid_without_writing():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="not currently discoverable: speaker-9"):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute("speaker-9")

    selected_group_repository.save_selected_group.assert_not_called()


def test_plan_sonos_selection_rejects_non_single_uid_input():
    sonos_service = MagicMock()

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=["speaker-1", "speaker-2"])

    assert plan.status == "invalid_request"
    assert "exactly one UID" in str(plan.error_message)


def test_plan_sonos_selection_auto_selects_only_visible_speaker():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute()

    assert plan.status == "resolved"
    assert plan.selected_uid == "speaker-1"


def test_plan_sonos_selection_requires_choice_when_multiple_speakers_available():
    sonos_service = MagicMock()
    available_speakers = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", host="192.168.1.31"),
    ]
    sonos_service.list_available_speakers.return_value = available_speakers

    plan = PlanSonosSelection(sonos_service=sonos_service).execute()

    assert plan.status == "needs_choice"
    assert plan.speakers == available_speakers


def test_plan_sonos_selection_reports_none_available_when_no_speakers_found():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = []

    plan = PlanSonosSelection(sonos_service=sonos_service).execute()

    assert plan.status == "none_available"
    assert plan.error_message == "No visible Sonos speakers found."


def test_get_sonos_selection_status_reports_not_selected_without_discovery():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = None
    sonos_service = MagicMock()

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is None
    assert status.availability.status == "not_selected"
    assert status.availability.speaker is None
    sonos_service.list_available_speakers.assert_not_called()


def test_get_sonos_selection_status_reports_available_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "available"
    assert status.availability.speaker is not None
    assert status.availability.speaker.host == "192.168.1.30"


def test_get_sonos_selection_status_reports_unavailable_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker(uid="speaker-2", host="192.168.1.31")]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert status.availability.speaker is None
