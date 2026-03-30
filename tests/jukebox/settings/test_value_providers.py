import pytest

from jukebox.settings.entities import ResolvedJukeboxRuntimeConfig
from jukebox.settings.validation_rules import VALIDATION_RULES
from jukebox.settings.value_providers import NestedMappingValueProvider, ResolvedJukeboxRuntimeValueProvider


def test_nested_mapping_value_provider_supports_nested_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.playback.pause_delay_seconds") is True
    assert provider.get_value("settings.playback.pause_delay_seconds") == 0.25


def test_nested_mapping_value_provider_rejects_unknown_paths():
    provider = NestedMappingValueProvider({"settings": {"playback": {"pause_delay_seconds": 0.25}}})

    assert provider.has_value("settings.runtime.pause_delay_seconds") is False

    with pytest.raises(KeyError, match="settings.runtime.pause_delay_seconds"):
        provider.get_value("settings.runtime.pause_delay_seconds")


def test_resolved_jukebox_runtime_value_provider_supports_runtime_validation_paths():
    provider = ResolvedJukeboxRuntimeValueProvider(
        ResolvedJukeboxRuntimeConfig(
            library_path="/tmp/library.json",
            player_type="dryrun",
            reader_type="dryrun",
            pause_duration_seconds=900,
            pause_delay_seconds=0.25,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.1,
        )
    )

    assert provider.has_value("jukebox.playback.pause_delay_seconds") is True
    assert provider.get_value("jukebox.playback.pause_delay_seconds") == 0.25


def test_resolved_jukebox_runtime_value_provider_rejects_unknown_paths():
    provider = ResolvedJukeboxRuntimeValueProvider(
        ResolvedJukeboxRuntimeConfig(
            library_path="/tmp/library.json",
            player_type="dryrun",
            reader_type="dryrun",
            pause_duration_seconds=900,
            pause_delay_seconds=0.25,
            loop_interval_seconds=0.1,
            nfc_read_timeout_seconds=0.1,
        )
    )

    assert provider.has_value("completely.wrong.pause_delay_seconds") is False

    with pytest.raises(KeyError, match="completely.wrong.pause_delay_seconds"):
        provider.get_value("completely.wrong.pause_delay_seconds")


def test_resolved_jukebox_runtime_value_provider_covers_all_runtime_rule_paths():
    assert ResolvedJukeboxRuntimeValueProvider.supported_paths() == {
        dependency_path for rule in VALIDATION_RULES for dependency_path in rule.depends_on_paths
    }
