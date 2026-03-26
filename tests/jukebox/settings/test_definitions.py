from jukebox.settings.definitions import get_profiles_affected_by_paths


def test_get_profiles_affected_by_paths_returns_jukebox_runtime_for_timing_settings():
    assert get_profiles_affected_by_paths(
        [
            "jukebox.playback.pause_delay_seconds",
            "jukebox.runtime.loop_interval_seconds",
        ]
    ) == ["jukebox_runtime"]


def test_get_profiles_affected_by_paths_returns_sorted_unique_profiles():
    assert get_profiles_affected_by_paths(
        [
            "admin.api.port",
            "paths.library_path",
            "jukebox.playback.pause_duration_seconds",
        ]
    ) == ["admin_runtime", "jukebox_runtime"]
