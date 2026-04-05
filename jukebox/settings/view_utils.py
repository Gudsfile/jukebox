from typing import Optional, cast

from .types import JsonObject

MISSING = object()


def lookup_object(root: JsonObject, key: str) -> JsonObject:
    value = root.get(key, {})
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return {}


def lookup_optional_dotted_path(root: JsonObject, dotted_path: str) -> object:
    current: JsonObject = root
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        child = current.get(part, MISSING)
        if not isinstance(child, dict):
            return MISSING
        current = cast(JsonObject, child)
    return current.get(parts[-1], MISSING)


def lookup_provenance_label(root: JsonObject, dotted_path: str) -> str:
    value = lookup_optional_dotted_path(root, dotted_path)
    collapsed_label = collapse_provenance_value(value)
    if collapsed_label is None:
        return "unknown"
    return collapsed_label


def collapse_provenance_value(value: object) -> Optional[str]:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None

    child_labels = []
    for child_value in value.values():
        child_label = collapse_provenance_value(child_value)
        if child_label is None:
            continue
        child_labels.append(child_label)

    if not child_labels:
        return None

    distinct_labels = set(child_labels)
    if len(distinct_labels) == 1:
        return child_labels[0]

    return "mixed"
