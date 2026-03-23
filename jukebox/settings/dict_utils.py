import copy

from .types import JsonObject


def deep_merge(base: JsonObject, overlay: JsonObject) -> JsonObject:
    result = copy.deepcopy(base)

    for key, value in overlay.items():
        current = result.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            result[key] = deep_merge(current, value)
            continue

        result[key] = copy.deepcopy(value)

    return result
