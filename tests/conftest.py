import sys

import pytest


@pytest.fixture()
def mock_lib_installed():
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
