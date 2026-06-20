from enum import StrEnum


class SettingsError(Exception):
    """Base exception for settings failures."""


class MalformedSettingsFileError(SettingsError):
    """Raised when the settings file cannot be parsed as JSON."""


class ErrorCode(StrEnum):
    """Exhaustive set of structured codes that drive CLI and API error presentation."""

    UNSUPPORTED_PATH = "unsupported_path"
    UNKNOWN_PATH = "unknown_path"
    INVALID_JSON_VALUE = "invalid_json_value"
    INVALID_JSON_TYPE = "invalid_json_type"
    INVALID_UPDATE = "invalid_update"
    INVALID_EFFECTIVE = "invalid_effective"
    INVALID_FILE = "invalid_file"


class InvalidSettingsError(SettingsError):
    """Raised when persisted or effective settings are invalid."""

    def __init__(self, message: str, *, code: ErrorCode, path: str | None = None):
        super().__init__(message)
        self.code = code
        self.path = path


class UnsupportedSettingsVersionError(SettingsError):
    """Raised when the settings file uses an unsupported schema version."""
