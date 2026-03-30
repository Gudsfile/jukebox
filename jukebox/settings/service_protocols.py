from typing import Protocol

from .entities import ResolvedAdminRuntimeConfig
from .types import JsonObject


class ReadOnlySettingsService(Protocol):
    def get_persisted_settings_view(self) -> JsonObject: ...

    def get_effective_settings_view(self) -> JsonObject: ...


class SettingsService(ReadOnlySettingsService, Protocol):
    def set_persisted_value(self, dotted_path: str, raw_value: str) -> JsonObject: ...

    def reset_persisted_value(self, dotted_path: str) -> JsonObject: ...

    def patch_persisted_settings(self, patch: JsonObject) -> JsonObject: ...

    def resolve_admin_runtime(self, verbose: bool = False) -> ResolvedAdminRuntimeConfig: ...
