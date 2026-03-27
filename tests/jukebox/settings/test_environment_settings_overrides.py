from unittest.mock import MagicMock

import pytest

from jukebox.settings.resolve import build_environment_settings_overrides


def test_build_environment_settings_overrides_reads_current_env_vars():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_LIBRARY_PATH", "/env/library.json")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/env/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None}}},
    }
    warning.assert_not_called()


def test_build_environment_settings_overrides_reads_deprecated_env_vars_with_warning():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("LIBRARY_PATH", "/deprecated/library.json")
        monkeypatch.setenv("SONOS_HOST", "192.168.1.20")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/deprecated/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": "192.168.1.20", "manual_name": None, "selected_group": None}}},
    }
    warning.assert_any_call("The LIBRARY_PATH environment variable is deprecated, use JUKEBOX_LIBRARY_PATH instead.")
    warning.assert_any_call("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    assert warning.call_count == 2


def test_build_environment_settings_overrides_prefers_current_env_vars_over_deprecated():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_LIBRARY_PATH", "/current/library.json")
        monkeypatch.setenv("LIBRARY_PATH", "/deprecated/library.json")
        monkeypatch.setenv("JUKEBOX_SONOS_HOST", "192.168.1.10")
        monkeypatch.setenv("SONOS_HOST", "192.168.1.20")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "paths": {"library_path": "/current/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": "192.168.1.10", "manual_name": None, "selected_group": None}}},
    }
    warning.assert_any_call("The LIBRARY_PATH environment variable is deprecated, use JUKEBOX_LIBRARY_PATH instead.")
    warning.assert_any_call("The SONOS_HOST environment variable is deprecated, use JUKEBOX_SONOS_HOST instead.")
    assert warning.call_count == 2


def test_build_environment_settings_overrides_preserves_conflicting_sonos_target_env_vars():
    warning = MagicMock()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_SONOS_HOST", "192.168.1.20")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")

        overrides = build_environment_settings_overrides(warning)

    assert overrides == {
        "jukebox": {
            "player": {
                "sonos": {
                    "manual_host": "192.168.1.20",
                    "manual_name": "Living Room",
                    "selected_group": None,
                }
            }
        }
    }
    warning.assert_not_called()
