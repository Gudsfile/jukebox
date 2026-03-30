import pytest

from jukebox.settings.value_providers import NestedMappingValueProvider


def test_nested_mapping_value_provider_supports_nested_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.playback.pause_delay_seconds") is True
    assert provider.get_value("settings.playback.pause_delay_seconds") == 0.25


def test_nested_mapping_value_provider_rejects_unknown_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.runtime.pause_delay_seconds") is False

    with pytest.raises(KeyError, match="settings.runtime.pause_delay_seconds"):
        provider.get_value("settings.runtime.pause_delay_seconds")
