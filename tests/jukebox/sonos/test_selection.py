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


def test_plan_sonos_selection_resolves_requested_group_and_defaults_coordinator():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(
        requested_uids=["speaker-1", "speaker-2"],
    )

    assert plan.status == "resolved"
    assert plan.selected_uids == ["speaker-1", "speaker-2"]
    assert plan.coordinator_uid == "speaker-1"


def test_plan_sonos_selection_resolves_requested_group_with_explicit_coordinator():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(
        requested_uids=["speaker-1", "speaker-2"],
        coordinator_uid="speaker-2",
    )

    assert plan.status == "resolved"
    assert plan.selected_uids == ["speaker-1", "speaker-2"]
    assert plan.coordinator_uid == "speaker-2"


def test_save_sonos_selection_persists_multi_member_selected_group_and_player_type():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult(
        message="Settings saved. Changes take effect after restart."
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    result = SaveSonosSelection(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute(["speaker-1", "speaker-2"], coordinator_uid="speaker-2")

    assert result.coordinator.uid == "speaker-2"
    assert [member.uid for member in result.members] == ["speaker-1", "speaker-2"]
    assert result.selected_group == SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    selected_group_repository.save_selected_group.assert_called_once_with(
        SelectedSonosGroupSettings(
            coordinator_uid="speaker-2",
            members=[
                SelectedSonosSpeakerSettings(uid="speaker-1"),
                SelectedSonosSpeakerSettings(uid="speaker-2"),
            ],
        )
    )


def test_plan_sonos_selection_rejects_unknown_uid():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=["speaker-9"])

    assert plan.status == "invalid_request"
    assert plan.error_message == "Selected Sonos speakers are not currently discoverable: speaker-9"


def test_save_sonos_selection_rejects_unknown_uid_without_writing():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="not currently discoverable: speaker-9"):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-9"])

    selected_group_repository.save_selected_group.assert_not_called()


def test_plan_sonos_selection_rejects_empty_uid_input():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=[])

    assert plan.status == "invalid_request"
    assert plan.error_message == "`uids` must include at least one UID."


def test_plan_sonos_selection_rejects_duplicate_uids():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(requested_uids=["speaker-1", "speaker-1"])

    assert plan.status == "invalid_request"
    assert plan.error_message == "`uids` must not contain duplicate UIDs."


def test_plan_sonos_selection_rejects_explicit_coordinator_outside_selected_group():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(
        requested_uids=["speaker-1"],
        coordinator_uid="speaker-2",
    )

    assert plan.status == "invalid_request"
    assert plan.error_message == "Selected Sonos coordinator must be one of the selected speakers: speaker-2"


def test_plan_sonos_selection_rejects_blank_coordinator_uid():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(
        requested_uids=["speaker-1", "speaker-2"],
        coordinator_uid="",
    )

    assert plan.status == "invalid_request"
    assert plan.error_message == "Selected Sonos coordinator must be one of the selected speakers: "


def test_plan_sonos_selection_rejects_mixed_household_input():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
    ]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute(
        requested_uids=["speaker-1", "speaker-2"],
    )

    assert plan.status == "invalid_request"
    assert plan.error_message == "Selected Sonos speakers must belong to the same household."


def test_plan_sonos_selection_auto_selects_only_visible_speaker():
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    plan = PlanSonosSelection(sonos_service=sonos_service).execute()

    assert plan.status == "resolved"
    assert plan.selected_uids == ["speaker-1"]
    assert plan.coordinator_uid == "speaker-1"


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
    assert status.availability.members == []
    sonos_service.list_available_speakers.assert_not_called()


def test_get_sonos_selection_status_reports_available_multi_speaker_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-2"
    assert status.availability.status == "available"
    assert [member.status for member in status.availability.members] == ["available", "available"]
    assert status.availability.members[1].speaker is not None
    assert status.availability.members[1].speaker.host == "192.168.1.31"


def test_get_sonos_selection_status_reports_partially_available_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker(uid="speaker-1")]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "partial"
    assert [member.status for member in status.availability.members] == ["available", "unavailable"]


def test_get_sonos_selection_status_reports_unavailable_selection_when_coordinator_is_missing():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker(uid="speaker-1", host="192.168.1.31")]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-2"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "unavailable"]


def test_get_sonos_selection_status_reports_unavailable_selection_for_mixed_households():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
    ]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "available"]


def test_get_sonos_selection_status_reports_unavailable_when_partial_group_spans_households():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
            SelectedSonosSpeakerSettings(uid="speaker-3"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [
        build_speaker(uid="speaker-1", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
    ]

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "available", "unavailable"]
