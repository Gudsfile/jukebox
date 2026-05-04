import pytest


@pytest.fixture
def walk_components():
    def _walk(components):
        for component in components:
            yield component
            children = getattr(component, "components", None)
            if children:
                yield from _walk(children)

    return _walk
