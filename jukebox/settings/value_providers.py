from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class SettingsValueProvider(Protocol):
    def has_value(self, dotted_path: str) -> bool: ...

    def get_value(self, dotted_path: str) -> Any: ...


@dataclass(frozen=True)
class NestedMappingValueProvider:
    values: Mapping[str, Any]

    def has_value(self, dotted_path: str) -> bool:
        current: Any = self.values

        for part in dotted_path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                return False
            current = current[part]

        return True

    def get_value(self, dotted_path: str) -> Any:
        current: Any = self.values

        for part in dotted_path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                raise KeyError(dotted_path)
            current = current[part]

        return current


@dataclass(frozen=True)
class ObjectLeafValueProvider:
    value_object: object

    def has_value(self, dotted_path: str) -> bool:
        return hasattr(self.value_object, _leaf_name(dotted_path))

    def get_value(self, dotted_path: str) -> Any:
        return getattr(self.value_object, _leaf_name(dotted_path))


def _leaf_name(dotted_path: str) -> str:
    return dotted_path.rsplit(".", 1)[-1]
