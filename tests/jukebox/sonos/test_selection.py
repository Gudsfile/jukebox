from unittest.mock import MagicMock

import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import (
    GetSonosSelectionStatus,
    SaveSelectedSonosGroupResult,
    SaveSonosSelection,
)
from jukebox.sonos.service import InspectedSelectedSonosGroup


def build_speaker(uid="speaker-1", name="Kitchen", host="192.168.1.30", household_id="household-1"):
    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def build_inspected_group(
    resolved_members,
    coordinator_uid,
    missing_member_uids=None,
    error_message=None,
):
    coordinator = next((member for member in resolved_members if member.uid == coordinator_uid), None)
    return InspectedSelectedSonosGroup(
        coordinator=coordinator,
        resolved_members=list(resolved_members),
        missing_member_uids=list(missing_member_uids or []),
        error_message=error_message,
    )


def test_save_sonos_selection_defaults_coordinator_to_first_selected_uid():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult(
        message="Settings saved. Changes take effect after restart."
    )
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    result = SaveSonosSelection(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute(["speaker-1", "speaker-2"])

    assert result.coordinator.uid == "speaker-1"
    assert [member.uid for member in result.members] == ["speaker-1", "speaker-2"]
    selected_group_repository.save_selected_group.assert_called_once_with(
        SelectedSonosGroupSettings(
            household_id="household-1",
            coordinator_uid="speaker-1",
            members=[
                SelectedSonosSpeakerSettings(uid="speaker-1"),
                SelectedSonosSpeakerSettings(uid="speaker-2"),
            ],
        )
    )
    sonos_service.list_network_speakers.assert_called_once_with()


def test_save_sonos_selection_persists_multi_member_selected_group_and_player_type():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult(
        message="Settings saved. Changes take effect after restart."
    )
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
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
        household_id="household-1",
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    selected_group_repository.save_selected_group.assert_called_once_with(
        SelectedSonosGroupSettings(
            household_id="household-1",
            coordinator_uid="speaker-2",
            members=[
                SelectedSonosSpeakerSettings(uid="speaker-1"),
                SelectedSonosSpeakerSettings(uid="speaker-2"),
            ],
        )
    )


def test_save_sonos_selection_validates_against_selectable_speakers():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [build_speaker(uid="speaker-9", household_id="household-2")]

    SaveSonosSelection(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute(["speaker-9"])

    sonos_service.list_network_speakers.assert_called_once_with()


def test_save_sonos_selection_rejects_unknown_uid_without_writing():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="not currently discoverable: speaker-9"):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-9"])

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_rejects_empty_uid_input():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="`uids` must include at least one UID."):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute([])

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_rejects_duplicate_uids():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="`uids` must not contain duplicate UIDs."):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-1", "speaker-1"])

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_rejects_explicit_coordinator_outside_selected_group():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    with pytest.raises(ValueError, match="Selected Sonos coordinator must be one of the selected speakers: speaker-2"):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-1"], coordinator_uid="speaker-2")

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_rejects_blank_coordinator_uid():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
        build_speaker(uid="speaker-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
    ]

    with pytest.raises(ValueError, match="Selected Sonos coordinator must be one of the selected speakers: "):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-1", "speaker-2"], coordinator_uid="")

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_rejects_mixed_household_input():
    selected_group_repository = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
        build_speaker(uid="speaker-1", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
    ]

    with pytest.raises(ValueError, match="Selected Sonos speakers must belong to the same household."):
        SaveSonosSelection(
            selected_group_repository=selected_group_repository,
            sonos_service=sonos_service,
        ).execute(["speaker-1", "speaker-2"])

    selected_group_repository.save_selected_group.assert_not_called()


def test_save_sonos_selection_persists_selected_household_id():
    selected_group_repository = MagicMock()
    selected_group_repository.save_selected_group.return_value = SaveSelectedSonosGroupResult()
    sonos_service = MagicMock()
    sonos_service.list_network_speakers.return_value = [
        build_speaker(uid="speaker-1", household_id="household-1"),
        build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-1"),
    ]

    result = SaveSonosSelection(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute(["speaker-1", "speaker-2"])

    assert [member.uid for member in result.members] == ["speaker-1", "speaker-2"]
    assert result.selected_group.household_id == "household-1"
    selected_group_repository.save_selected_group.assert_called_once_with(
        SelectedSonosGroupSettings(
            household_id="household-1",
            coordinator_uid="speaker-1",
            members=[
                SelectedSonosSpeakerSettings(uid="speaker-1"),
                SelectedSonosSpeakerSettings(uid="speaker-2"),
            ],
        )
    )


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
    sonos_service.inspect_selected_group.assert_not_called()


def test_get_sonos_selection_status_reports_available_multi_speaker_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        household_id="household-1",
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
            build_speaker(uid="speaker-1"),
            build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31"),
        ],
        coordinator_uid="speaker-2",
    )

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is not None
    assert status.selected_group.coordinator_uid == "speaker-2"
    assert status.availability.status == "available"
    assert [member.status for member in status.availability.members] == ["available", "available"]
    assert status.availability.members[1].speaker is not None
    assert status.availability.members[1].speaker.host == "192.168.1.31"


def test_get_sonos_selection_status_reports_partially_available_selection():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        household_id="household-1",
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[build_speaker(uid="speaker-1")],
        coordinator_uid="speaker-1",
        missing_member_uids=["speaker-2"],
    )

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is not None
    assert status.selected_group.coordinator_uid == "speaker-1"
    assert status.availability.status == "partial"
    assert [member.status for member in status.availability.members] == ["available", "unavailable"]


def test_get_sonos_selection_status_reports_unavailable_selection_when_coordinator_is_missing():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        household_id="household-1",
        coordinator_uid="speaker-2",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[build_speaker(uid="speaker-1", host="192.168.1.31")],
        coordinator_uid="speaker-2",
        error_message="Unable to resolve saved Sonos coordinator: speaker-2: not found on network",
    )

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is not None
    assert status.selected_group.coordinator_uid == "speaker-2"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "unavailable"]


def test_get_sonos_selection_status_reports_unavailable_selection_for_mixed_households():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        household_id="household-1",
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
            build_speaker(uid="speaker-1", household_id="household-1"),
            build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
        ],
        coordinator_uid="speaker-1",
        error_message="Resolved Sonos group members must belong to the same household",
    )

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is not None
    assert status.selected_group.coordinator_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "available"]


def test_get_sonos_selection_status_reports_unavailable_when_partial_group_spans_households():
    selected_group_repository = MagicMock()
    selected_group_repository.get_selected_group.return_value = SelectedSonosGroupSettings(
        household_id="household-1",
        coordinator_uid="speaker-1",
        members=[
            SelectedSonosSpeakerSettings(uid="speaker-1"),
            SelectedSonosSpeakerSettings(uid="speaker-2"),
            SelectedSonosSpeakerSettings(uid="speaker-3"),
        ],
    )
    sonos_service = MagicMock()
    sonos_service.inspect_selected_group.return_value = build_inspected_group(
        resolved_members=[
            build_speaker(uid="speaker-1", household_id="household-1"),
            build_speaker(uid="speaker-2", name="Living Room", host="192.168.1.31", household_id="household-2"),
        ],
        coordinator_uid="speaker-1",
        missing_member_uids=["speaker-3"],
        error_message="Resolved Sonos group members must belong to the same household",
    )

    status = GetSonosSelectionStatus(
        selected_group_repository=selected_group_repository,
        sonos_service=sonos_service,
    ).execute()

    assert status.selected_group is not None
    assert status.selected_group.coordinator_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert [member.status for member in status.availability.members] == ["available", "available", "unavailable"]
