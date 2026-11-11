from .dict_utils import deep_merge
from .entities import PersistedAppSettings, SparsePersistedAppSettings
from .migration import migrate_settings_data
from .types import JsonObject, JsonValue


def migrate_and_validate_persisted_settings_data(raw_data: JsonValue) -> tuple[JsonObject, bool]:
    """Migrate raw persisted settings to the current schema and check their shape.

    Raises InvalidSettingsError or UnsupportedSettingsVersionError for the schema version,
    and pydantic's ValidationError for the content.
    """
    migrated_data, migrated = migrate_settings_data(raw_data)
    SparsePersistedAppSettings.model_validate(migrated_data)
    PersistedAppSettings.model_validate(deep_merge(PersistedAppSettings().model_dump(mode="python"), migrated_data))
    return migrated_data, migrated
