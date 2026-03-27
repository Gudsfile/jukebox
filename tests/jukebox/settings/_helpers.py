from typing import cast

from jukebox.settings.types import JsonObject, JsonValue


def lookup_json_value(root: JsonObject, *path: str) -> JsonValue:
    current: JsonValue = root

    for part in path:
        assert isinstance(current, dict)
        current = current[part]

    return current


def lookup_json_object(root: JsonObject, *path: str) -> JsonObject:
    value = lookup_json_value(root, *path)
    assert isinstance(value, dict)
    return cast(JsonObject, value)
