from unittest.mock import MagicMock

import pytest

from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.sonos.discovery import DiscoveredSonosSpeaker
from jukebox.sonos.selection import (
    GetSonosSelectionStatus,
    SelectDefaultSonosSpeaker,
)


def build_speaker(uid="speaker-1", name="Kitchen", host="192.168.1.30", household_id="household-1"):
    return DiscoveredSonosSpeaker(
        uid=uid,
        name=name,
        host=host,
        household_id=household_id,
        is_visible=True,
    )


def test_select_default_sonos_speaker_persists_one_member_selected_group_and_player_type():
    settings_service = MagicMock()
    settings_service.patch_persisted_settings.return_value = {
        "message": "Settings saved. Changes take effect after restart."
    }
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    result = SelectDefaultSonosSpeaker(settings_service=settings_service, sonos_service=sonos_service).execute(
        "speaker-1"
    )

    assert result.speaker.uid == "speaker-1"
    assert result.selected_group == SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )
    settings_service.patch_persisted_settings.assert_called_once_with(
        {
            "jukebox": {
                "player": {
                    "type": "sonos",
                    "sonos": {
                        "selected_group": {
                            "coordinator_uid": "speaker-1",
                            "members": [{"uid": "speaker-1"}],
                        }
                    },
                }
            }
        }
    )


def test_select_default_sonos_speaker_rejects_unknown_uid_without_writing():
    settings_service = MagicMock()
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    with pytest.raises(ValueError, match="not currently discoverable: speaker-9"):
        SelectDefaultSonosSpeaker(settings_service=settings_service, sonos_service=sonos_service).execute("speaker-9")

    settings_service.patch_persisted_settings.assert_not_called()


def test_get_sonos_selection_status_reports_not_selected_without_discovery():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {"schema_version": 1}
    sonos_service = MagicMock()

    status = GetSonosSelectionStatus(settings_service=settings_service, sonos_service=sonos_service).execute()

    assert status.selected_group is None
    assert status.availability.status == "not_selected"
    assert status.availability.speaker is None
    sonos_service.list_available_speakers.assert_not_called()


def test_get_sonos_selection_status_reports_available_selection():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}],
                    }
                }
            }
        },
    }
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker()]

    status = GetSonosSelectionStatus(settings_service=settings_service, sonos_service=sonos_service).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "available"
    assert status.availability.speaker is not None
    assert status.availability.speaker.host == "192.168.1.30"


def test_get_sonos_selection_status_reports_unavailable_selection():
    settings_service = MagicMock()
    settings_service.get_persisted_settings_view.return_value = {
        "schema_version": 1,
        "jukebox": {
            "player": {
                "sonos": {
                    "selected_group": {
                        "coordinator_uid": "speaker-1",
                        "members": [{"uid": "speaker-1"}],
                    }
                }
            }
        },
    }
    sonos_service = MagicMock()
    sonos_service.list_available_speakers.return_value = [build_speaker(uid="speaker-2", host="192.168.1.31")]

    status = GetSonosSelectionStatus(settings_service=settings_service, sonos_service=sonos_service).execute()

    assert status.selected_uid == "speaker-1"
    assert status.availability.status == "unavailable"
    assert status.availability.speaker is None
