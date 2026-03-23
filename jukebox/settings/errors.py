class SettingsError(Exception):
    """Base exception for settings failures."""


class MalformedSettingsFileError(SettingsError):
    """Raised when the settings file cannot be parsed as JSON."""


class InvalidSettingsError(SettingsError):
    """Raised when persisted or effective settings are invalid."""


class UnsupportedSettingsVersionError(SettingsError):
    """Raised when the settings file uses an unsupported schema version."""
