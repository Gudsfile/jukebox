import sys

import pytest


@pytest.fixture()
def mock_pn532_lib_installed():
    def lib_func():
        print("lib_func called")

    module = type(sys)("pn532")
    module.submodule = type(sys)("PN532_SPI")
    module.submodule.lib_func = lib_func
    sys.modules["pn532"] = module
    sys.modules["pn532.PN532_SPI"] = module.submodule

    yield

    del sys.modules["pn532"]
    del sys.modules["pn532.PN532_SPI"]


def test_parse_raw_uid(mock_pn532_lib_installed):
    from jukebox.adapters.outbound.readers.nfc_reader_adapter import parse_raw_uid

    raw_uid = bytearray(b"\x04\xf2=v\x8fa\x80")
    assert parse_raw_uid(raw_uid) == "04:f2:3d:76:8f:61:80"


def test_dependencies_import_failure(mocker):
    sys.modules.pop("jukebox.adapters.outbound.readers.nfc_reader_adapter", None)
    mocker.patch.dict("sys.modules", {"pn532": None})

    with pytest.raises(ModuleNotFoundError) as err:
        import jukebox.adapters.outbound.readers.nfc_reader_adapter

    assert "The `nfc reader` requires `pip install gukebox[nfc]`." in str(err.value)


# Note: NfcReaderAdapter tests would require hardware mocking (PN532_SPI)
# which is complex and not critical since it's a thin wrapper.
