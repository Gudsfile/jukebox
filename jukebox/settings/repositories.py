from typing import Protocol

from .entities import PersistedAppSettings
from .types import JsonObject


class SettingsRepository(Protocol):
    def load_persisted(self) -> PersistedAppSettings: ...

    def load_persisted_settings_data(self) -> JsonObject: ...

    def save_persisted_settings_data(self, data: JsonObject) -> None: ...
