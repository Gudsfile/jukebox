from jukebox.shared.config_utils import get_current_tag_path


def test_current_tag_paths_are_derived_beside_library(tmp_path):
    library_path = tmp_path / "nested" / "library.json"

    assert get_current_tag_path(str(library_path)) == str(tmp_path / "nested" / "current-tag.txt")
