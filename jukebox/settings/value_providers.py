from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol


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
    dotted_path_to_attribute: Optional[Mapping[str, str]] = None

    def has_value(self, dotted_path: str) -> bool:
        attribute_name = self._get_attribute_name(dotted_path)
        return attribute_name is not None and hasattr(self.value_object, attribute_name)

    def get_value(self, dotted_path: str) -> Any:
        attribute_name = self._get_attribute_name(dotted_path)
        if attribute_name is None or not hasattr(self.value_object, attribute_name):
            raise KeyError(dotted_path)

        return getattr(self.value_object, attribute_name)

    def _get_attribute_name(self, dotted_path: str) -> Optional[str]:
        if self.dotted_path_to_attribute is not None:
            return self.dotted_path_to_attribute.get(dotted_path)

        if "." in dotted_path:
            return None

        return dotted_path
