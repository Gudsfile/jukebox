from typing import Any

import pytest


@pytest.fixture
def get_route():
    def _get_route(router: Any, path: str, method: str) -> Any:
        return next(
            route
            for route in router.routes
            if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
        )

    return _get_route
