from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Mapping, Protocol

if TYPE_CHECKING:
    from .entities import ResolvedJukeboxRuntimeConfig


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
class ResolvedJukeboxRuntimeValueProvider:
    runtime_config: "ResolvedJukeboxRuntimeConfig"
    PATH_TO_ATTRIBUTE: ClassVar[Mapping[str, str]] = {
        "jukebox.playback.pause_delay_seconds": "pause_delay_seconds",
        "jukebox.runtime.loop_interval_seconds": "loop_interval_seconds",
    }

    def has_value(self, dotted_path: str) -> bool:
        attribute_name = self._get_attribute_name(dotted_path)
        return attribute_name is not None and hasattr(self.runtime_config, attribute_name)

    def get_value(self, dotted_path: str) -> Any:
        attribute_name = self._get_attribute_name(dotted_path)
        if attribute_name is None or not hasattr(self.runtime_config, attribute_name):
            raise KeyError(dotted_path)

        return getattr(self.runtime_config, attribute_name)

    @classmethod
    def supported_paths(cls) -> set[str]:
        return set(cls.PATH_TO_ATTRIBUTE)

    def _get_attribute_name(self, dotted_path: str) -> Any:
        return self.PATH_TO_ATTRIBUTE.get(dotted_path)
