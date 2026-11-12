import importlib.util

import pytest

FASTAPI_INSTALLED = importlib.util.find_spec("fastapi") is not None

if FASTAPI_INSTALLED:
    from jukebox.adapters.inbound.admin.api.version_router import VersionOutput, build_version_router


@pytest.mark.skipif(not FASTAPI_INSTALLED, reason="FastAPI dependencies are not installed")
def test_get_version_returns_the_installed_version(get_route):
    router = build_version_router(get_version=lambda: "1.10.0.dev3")
    route = get_route(router, "/api/v1/version", "GET")

    assert route.endpoint() == VersionOutput(version="1.10.0.dev3")
