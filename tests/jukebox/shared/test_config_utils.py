from jukebox.shared.config_utils import get_current_disc_lock_path, get_current_disc_path


def test_current_disc_paths_are_derived_beside_library(tmp_path):
    library_path = tmp_path / "nested" / "library.json"

    assert get_current_disc_path(str(library_path)) == str(tmp_path / "nested" / "current-disc.json")
    assert get_current_disc_lock_path(str(library_path)) == str(tmp_path / "nested" / "current-disc.lock")
