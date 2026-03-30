from types import SimpleNamespace

import pytest

from jukebox.settings.value_providers import NestedMappingValueProvider, ObjectLeafValueProvider


def test_nested_mapping_value_provider_supports_nested_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.playback.pause_delay_seconds") is True
    assert provider.get_value("settings.playback.pause_delay_seconds") == 0.25


def test_nested_mapping_value_provider_rejects_unknown_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.runtime.pause_delay_seconds") is False

    with pytest.raises(KeyError, match="settings.runtime.pause_delay_seconds"):
        provider.get_value("settings.runtime.pause_delay_seconds")


def test_object_leaf_value_provider_uses_explicit_dotted_path_mapping():
    provider = ObjectLeafValueProvider(
        SimpleNamespace(pause_delay_seconds=0.25),
        {"jukebox.playback.pause_delay_seconds": "pause_delay_seconds"},
    )

    assert provider.has_value("jukebox.playback.pause_delay_seconds") is True
    assert provider.get_value("jukebox.playback.pause_delay_seconds") == 0.25


def test_object_leaf_value_provider_rejects_wrong_prefix_for_same_leaf():
    provider = ObjectLeafValueProvider(
        SimpleNamespace(pause_delay_seconds=0.25),
        {"jukebox.playback.pause_delay_seconds": "pause_delay_seconds"},
    )

    assert provider.has_value("completely.wrong.pause_delay_seconds") is False

    with pytest.raises(KeyError, match="completely.wrong.pause_delay_seconds"):
        provider.get_value("completely.wrong.pause_delay_seconds")
