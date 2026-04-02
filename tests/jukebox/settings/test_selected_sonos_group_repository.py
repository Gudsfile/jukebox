from jukebox.settings.entities import SelectedSonosGroupSettings, SelectedSonosSpeakerSettings
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository


def test_get_selected_group_returns_none_when_not_persisted():
    settings_service = type(
        "StubSettingsService",
        (),
        {"get_persisted_settings_view": lambda self: {"schema_version": 1}},
    )()

    repository = SettingsSelectedSonosGroupRepository(settings_service)

    assert repository.get_selected_group() is None


def test_get_selected_group_loads_saved_group_from_settings_schema():
    settings_service = type(
        "StubSettingsService",
        (),
        {
            "get_persisted_settings_view": lambda self: {
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
        },
    )()

    repository = SettingsSelectedSonosGroupRepository(settings_service)

    assert repository.get_selected_group() == SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )


def test_save_selected_group_persists_through_settings_service():
    class StubSettingsService:
        def __init__(self):
            self.patch = None

        def patch_persisted_settings(self, patch):
            self.patch = patch
            return {
                "message": "Settings saved. Changes take effect after restart.",
                "restart_required": True,
            }

    settings_service = StubSettingsService()
    repository = SettingsSelectedSonosGroupRepository(settings_service)
    selected_group = SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )

    result = repository.save_selected_group(selected_group)

    assert settings_service.patch == {
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
    assert result.message == "Settings saved. Changes take effect after restart."
    assert result.restart_required is True
