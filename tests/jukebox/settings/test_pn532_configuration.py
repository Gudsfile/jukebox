from unittest.mock import MagicMock, call

from jukebox.settings.pn532_configuration import save_pn532_configuration


def test_save_pn532_configuration_resets_default_protocol_and_pins_matching_profile_defaults():
    service = MagicMock()

    save_pn532_configuration(service, "waveshare_hat", "spi", {"reset": 20, "cs": "8", "irq": None})

    assert service.method_calls == [
        call.set_persisted_value("jukebox.reader.pn532.board_profile", "waveshare_hat"),
        call.reset_persisted_value("jukebox.reader.pn532.protocol"),
        call.reset_persisted_value("jukebox.reader.pn532.spi.reset"),
        call.set_persisted_value("jukebox.reader.pn532.spi.cs", "8"),
        call.reset_persisted_value("jukebox.reader.pn532.spi.irq"),
    ]


def test_save_pn532_configuration_persists_non_integer_pins_for_settings_validation_to_reject():
    service = MagicMock()

    save_pn532_configuration(service, "custom", "spi", {"reset": "abc", "cs": None, "irq": None})

    service.set_persisted_value.assert_any_call("jukebox.reader.pn532.spi.reset", "abc")
