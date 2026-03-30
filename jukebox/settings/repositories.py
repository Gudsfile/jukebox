from typing import Protocol

from .entities import AppSettings
from .types import JsonObject


class SettingsRepository(Protocol):
    def load(self) -> AppSettings: ...

    def load_persisted_settings_data(self) -> JsonObject: ...

    def save_persisted_settings_data(self, data: JsonObject) -> None: ...
