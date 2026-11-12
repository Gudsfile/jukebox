from importlib.metadata import PackageNotFoundError

from jukebox.shared.config_utils import get_package_version


def test_get_package_version_returns_the_installed_version(mocker):
    mocker.patch("jukebox.shared.config_utils.version", return_value="1.10.0.dev3")

    assert get_package_version() == "1.10.0.dev3"


def test_get_package_version_returns_unknown_when_the_package_is_not_installed(mocker):
    mocker.patch("jukebox.shared.config_utils.version", side_effect=PackageNotFoundError("gukebox"))

    assert get_package_version() == "unknown"
