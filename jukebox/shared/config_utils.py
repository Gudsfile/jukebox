import argparse
import logging
import os
from typing import Callable, Optional

try:
    from importlib.metadata import PackageNotFoundError, version  # type: ignore[unresolved-import]
except ImportError:
    from importlib_metadata import PackageNotFoundError, version  # type: ignore[unresolved-import]


DEFAULT_LIBRARY_PATH = os.path.expanduser("~/.jukebox/library.json")
LOGGER = logging.getLogger("jukebox")


def get_package_version(package_name: str = "gukebox") -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def get_deprecated_env_with_warning(
    new_var: str,
    deprecated_var: str,
    default: Optional[str],
    logger_warning: Callable[[str], None],
) -> Optional[str]:
    deprecated_value = os.environ.get(deprecated_var)
    if deprecated_value:
        logger_warning(f"The {deprecated_var} environment variable is deprecated, use {new_var} instead.")
    return os.environ.get(new_var, deprecated_value or default)


def add_library_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-l",
        "--library",
        default=get_deprecated_env_with_warning(
            "JUKEBOX_LIBRARY_PATH",
            "LIBRARY_PATH",
            DEFAULT_LIBRARY_PATH,
            LOGGER.warning,
        ),
        help="path to the library JSON file",
    )


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
