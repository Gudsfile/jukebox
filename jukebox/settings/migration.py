import copy

from .errors import InvalidSettingsError, UnsupportedSettingsVersionError
from .types import JsonObject, JsonValue

CURRENT_SETTINGS_SCHEMA_VERSION = 1


def migrate_settings_data(data: JsonValue) -> tuple[JsonObject, bool]:
    if not isinstance(data, dict):
        raise InvalidSettingsError("The settings file root must be a JSON object.")

    migrated_data = copy.deepcopy(data)
    schema_version = migrated_data.get("schema_version")

    if schema_version is None:
        migrated_data["schema_version"] = CURRENT_SETTINGS_SCHEMA_VERSION
        return migrated_data, True

    if not isinstance(schema_version, int):
        raise InvalidSettingsError("The settings file schema_version must be an integer.")

    if schema_version == CURRENT_SETTINGS_SCHEMA_VERSION:
        return migrated_data, False

    if schema_version == 0:
        migrated_data["schema_version"] = CURRENT_SETTINGS_SCHEMA_VERSION
        return migrated_data, True

    if schema_version > CURRENT_SETTINGS_SCHEMA_VERSION:
        raise UnsupportedSettingsVersionError(
            "Unsupported settings schema_version "
            f"{schema_version}; this build supports version {CURRENT_SETTINGS_SCHEMA_VERSION}."
        )

    raise UnsupportedSettingsVersionError(
        "Unsupported legacy settings schema_version "
        f"{schema_version}; only version {CURRENT_SETTINGS_SCHEMA_VERSION} is supported."
    )
