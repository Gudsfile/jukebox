import dataclasses
from collections.abc import Mapping

from jukebox.pn532.profiles import PN532_PROFILES, Pn532BoardProfile, Pn532Protocol

from .service_protocols import SettingsService


def save_pn532_configuration(
    settings_service: SettingsService,
    board_profile: Pn532BoardProfile,
    protocol: Pn532Protocol,
    pins: Mapping[str, str | int | None],
) -> None:
    """Persist a PN532 board profile, protocol and pin overrides.

    Values equal to the profile defaults are reset rather than persisted, so they keep
    following the profile if it changes. A pin value of None means "use the profile default".
    """
    profile = PN532_PROFILES[board_profile]
    pin_defaults = profile.connections[protocol]

    settings_service.set_persisted_value("jukebox.reader.pn532.board_profile", board_profile)
    if protocol != profile.default_protocol:
        settings_service.set_persisted_value("jukebox.reader.pn532.protocol", protocol)
    else:
        settings_service.reset_persisted_value("jukebox.reader.pn532.protocol")

    for field in dataclasses.fields(pin_defaults):
        path = f"jukebox.reader.pn532.{protocol}.{field.name}"
        value = pins[field.name]
        try:
            is_default = value is None or int(value) == getattr(pin_defaults, field.name)
        except ValueError:
            is_default = False
        if is_default:
            settings_service.reset_persisted_value(path)
        else:
            settings_service.set_persisted_value(path, str(value))
