from typing import Protocol

from .types import JsonObject


class ReadOnlySettingsService(Protocol):
    def get_persisted_settings_view(self) -> JsonObject: ...

    def get_effective_settings_view(self) -> JsonObject: ...
