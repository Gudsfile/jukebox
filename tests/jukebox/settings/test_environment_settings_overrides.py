import pytest

from jukebox.settings.resolve import build_environment_settings_overrides


def test_build_environment_settings_overrides_reads_current_env_vars():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_LIBRARY_PATH", "/env/library.json")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")

        overrides = build_environment_settings_overrides()

    assert overrides == {
        "paths": {"library_path": "/env/library.json"},
        "jukebox": {"player": {"sonos": {"manual_host": None, "manual_name": "Living Room", "selected_group": None}}},
    }


def test_build_environment_settings_overrides_preserves_conflicting_sonos_target_env_vars():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("JUKEBOX_SONOS_HOST", "192.168.1.20")
        monkeypatch.setenv("JUKEBOX_SONOS_NAME", "Living Room")

        overrides = build_environment_settings_overrides()

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
