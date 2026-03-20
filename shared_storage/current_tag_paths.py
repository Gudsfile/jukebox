import os


def get_current_tag_path(library_path: str) -> str:
    library_dir = os.path.dirname(os.path.abspath(os.path.expanduser(library_path)))
    return os.path.join(library_dir, "current-tag.txt")
