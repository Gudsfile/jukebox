from pytest import raises

from jukebox.readers import get_reader
from jukebox.readers.dryrun import DryRunReader


def test_get_dryrun_should_return_dryrun_reader_type():
    """Test if the dryrun reader type is returned"""
    assert get_reader("dryrun") == DryRunReader


def test_get_nfc_should_return_nfc_reader_type(mock_lib_installed):
    """Test if the nfc reader type is returned"""
    from jukebox.readers.nfc import NFCReader

    assert get_reader("nfc") == NFCReader


def test_get_reader_should_raise_an_error_if_unknown_reader_name_is_provided():
    """Test if an error is raised if an unknown reader name is provided"""
    with raises(ValueError) as excinfo:
        get_reader("not-implemented-reader")

    assert str(excinfo.value) == "The `not-implemented-reader` reader is not yet implemented."
