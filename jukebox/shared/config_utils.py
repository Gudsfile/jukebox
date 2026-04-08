import argparse
import os
from importlib.metadata import PackageNotFoundError, version


def get_package_version(package_name: str = "gukebox") -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def get_current_tag_path(library_path: str) -> str:
    library_dir = os.path.dirname(os.path.abspath(os.path.expanduser(library_path)))
    return os.path.join(library_dir, "current-tag.txt")


def add_verbose_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable verbose logging",
    )


def add_version_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_package_version()}",
        help="show current installed version",
    )
