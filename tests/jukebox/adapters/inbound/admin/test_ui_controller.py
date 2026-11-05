import importlib.util
from unittest.mock import MagicMock

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from starlette.routing import Mount

    from jukebox.adapters.inbound.admin.ui_controller import UIController

pytestmark = pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")


def build_controller():
    return UIController(*(MagicMock() for _ in range(8)))


def test_admin_ui_static_bundle_is_mounted_at_root():
    controller = build_controller()

    mount = next(route for route in controller.app.routes if isinstance(route, Mount))

    assert mount.path == ""
    assert mount.name == "admin-ui"


def test_admin_ui_mount_is_registered_last_so_it_does_not_shadow_other_routes():
    controller = build_controller()

    assert isinstance(controller.app.routes[-1], Mount)
    assert any(getattr(route, "path", None) == "/api/v1/sonos/speakers" for route in controller.app.routes[:-1])
