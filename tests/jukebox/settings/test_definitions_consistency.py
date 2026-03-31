from typing import Any, Optional, get_args, get_origin

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import BaseModel

from jukebox.settings.definitions import SETTINGS
from jukebox.settings.entities import PersistedAppSettings


def test_editable_setting_definitions_match_persisted_settings_schema():
    persisted_paths = _collect_model_paths(PersistedAppSettings)

    for dotted_path, definition in SETTINGS.items():
        assert dotted_path in persisted_paths, f"{dotted_path} is not present in PersistedAppSettings"
        assert persisted_paths[dotted_path] == definition.field_type


def _collect_model_paths(model_type: type[BaseModel], prefix: str = "") -> dict[str, str]:
    paths = {}

    for field_name, field_info in model_type.model_fields.items():
        dotted_path = f"{prefix}.{field_name}" if prefix else field_name
        field_type = _field_type_name(field_info.annotation)
        paths[dotted_path] = field_type

        nested_model_type = _extract_model_type(field_info.annotation)
        if nested_model_type is not None:
            paths.update(_collect_model_paths(nested_model_type, dotted_path))

    return paths


def _field_type_name(annotation: Any) -> str:
    annotation = _strip_none(annotation)
    origin = get_origin(annotation)

    if origin is Literal:
        literal_values = get_args(annotation)
        if literal_values and all(isinstance(value, str) for value in literal_values):
            return "string"
        raise AssertionError(f"Unsupported Literal annotation: {annotation!r}")

    if origin is list:
        return "array"

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return "object"

    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    if annotation is str:
        return "string"

    raise AssertionError(f"Unsupported field annotation: {annotation!r}")


def _extract_model_type(annotation: Any) -> Optional[type[BaseModel]]:
    annotation = _strip_none(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _strip_none(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation

    args = tuple(arg for arg in get_args(annotation) if arg is not type(None))
    if len(args) == 1:
        return args[0]

    return annotation
