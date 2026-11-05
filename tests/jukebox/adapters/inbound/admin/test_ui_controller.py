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


def test_warns_when_admin_ui_bundle_is_missing(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("jukebox.adapters.inbound.admin.ui_controller.STATIC_DIR", tmp_path)

    with caplog.at_level("WARNING", logger="jukebox"):
        build_controller()

    assert "Admin UI bundle not found" in caplog.text


def test_does_not_warn_when_admin_ui_bundle_is_present(tmp_path, monkeypatch, caplog):
    (tmp_path / "index.html").write_text("<!doctype html>")
    monkeypatch.setattr("jukebox.adapters.inbound.admin.ui_controller.STATIC_DIR", tmp_path)

    with caplog.at_level("WARNING", logger="jukebox"):
        build_controller()

    assert "Admin UI bundle not found" not in caplog.text
