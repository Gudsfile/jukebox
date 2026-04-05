from typing import Optional

from jukebox.settings.entities import (
    ResolvedAdminRuntimeConfig,
    SelectedSonosGroupSettings,
    SelectedSonosSpeakerSettings,
)
from jukebox.settings.selected_sonos_group_repository import SettingsSelectedSonosGroupRepository
from jukebox.settings.types import JsonObject


class StubSettingsService:
    def __init__(
        self,
        persisted_view: Optional[JsonObject] = None,
        patch_result: Optional[JsonObject] = None,
    ):
        if persisted_view is None:
            persisted_view = {"schema_version": 1}
        if patch_result is None:
            patch_result = {
                "message": "Settings saved. Changes take effect after restart.",
                "restart_required": True,
            }
        self.persisted_view: JsonObject = persisted_view
        self.patch_result: JsonObject = patch_result
        self.patch = None

    def get_persisted_settings_view(self) -> JsonObject:
        return self.persisted_view

    def get_effective_settings_view(self) -> JsonObject:
        raise AssertionError("get_effective_settings_view should not be called in this test")

    def set_persisted_value(self, dotted_path: str, raw_value: str) -> JsonObject:
        raise AssertionError("set_persisted_value should not be called in this test")

    def reset_persisted_value(self, dotted_path: str) -> JsonObject:
        raise AssertionError("reset_persisted_value should not be called in this test")

    def patch_persisted_settings(self, patch: JsonObject) -> JsonObject:
        self.patch = patch
        return self.patch_result

    def resolve_admin_runtime(self, verbose: bool = False) -> ResolvedAdminRuntimeConfig:
        raise AssertionError("resolve_admin_runtime should not be called in this test")


def test_get_selected_group_returns_none_when_not_persisted():
    settings_service = StubSettingsService()

    repository = SettingsSelectedSonosGroupRepository(settings_service)

    assert repository.get_selected_group() is None


def test_get_selected_group_loads_saved_group_from_settings_schema():
    settings_service = StubSettingsService(
        persisted_view={
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
    )

    repository = SettingsSelectedSonosGroupRepository(settings_service)

    assert repository.get_selected_group() == SelectedSonosGroupSettings(
        coordinator_uid="speaker-1",
        members=[SelectedSonosSpeakerSettings(uid="speaker-1")],
    )


def test_save_selected_group_persists_through_settings_service():
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
