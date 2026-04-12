from typing import Optional, cast

from jukebox.settings.entities import (
    ResolvedSonosGroupRuntime,
    ResolvedSonosSpeakerRuntime,
)
from jukebox.settings.resolve import SettingsService
from jukebox.settings.runtime_resolver import JukeboxRuntimeResolver
from jukebox.settings.types import JsonObject, JsonValue


def lookup_json_value(root: JsonObject, *path: str) -> JsonValue:
    current: JsonValue = root

    for part in path:
        assert isinstance(current, dict)
        current = current[part]

    return current


def lookup_json_object(root: JsonObject, *path: str) -> JsonObject:
    value = lookup_json_value(root, *path)
    assert isinstance(value, dict)
    return cast(JsonObject, value)


def build_resolved_sonos_group_runtime(
    coordinator_uid: str = "speaker-1",
    speakers: Optional[list[tuple[str, str, str, str]]] = None,
    household_id: str = "household-1",
    missing_member_uids: Optional[list[str]] = None,
) -> ResolvedSonosGroupRuntime:
    speakers = speakers or [("speaker-1", "Living Room", "192.168.1.20", household_id)]
    members = [
        ResolvedSonosSpeakerRuntime(uid=uid, name=name, host=host, household_id=member_household_id)
        for uid, name, host, member_household_id in speakers
    ]
    coordinator = next(member for member in members if member.uid == coordinator_uid)
    return ResolvedSonosGroupRuntime(
        household_id=household_id,
        coordinator=coordinator,
        members=members,
        missing_member_uids=missing_member_uids or [],
    )


class StubSonosService:
    def __init__(
        self,
        resolved_group: Optional[ResolvedSonosGroupRuntime] = None,
        error: Optional[Exception] = None,
    ):
        self.resolved_group = resolved_group
        self.error = error
        self.calls = []

    def resolve_selected_group(self, selected_group):
        self.calls.append(selected_group)
        if self.error is not None:
            raise self.error
        assert self.resolved_group is not None
        return self.resolved_group

    def list_available_speakers(self):
        return []


def resolve_jukebox_runtime(
    settings_service: SettingsService,
    sonos_service: Optional[StubSonosService] = None,
    verbose: bool = False,
):
    if sonos_service is None:
        sonos_service = StubSonosService(error=AssertionError("sonos_service should not be called"))

    return JukeboxRuntimeResolver(settings_service, sonos_service).resolve(verbose=verbose)
