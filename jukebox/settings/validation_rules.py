from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .timing_validation import validate_loop_interval_lower_than_pause_delay


@dataclass(frozen=True)
class SettingsValidationRule:
    name: str
    depends_on_paths: tuple[str, ...]
    validator: Callable[..., None]

    def validate(self, settings: Mapping[str, Any]) -> None:
        values = [_get_dotted_path(settings, dotted_path) for dotted_path in self.depends_on_paths]
        self.validator(*values)


VALIDATION_RULES = (
    SettingsValidationRule(
        name="loop_interval_lower_than_pause_delay",
        depends_on_paths=(
            "jukebox.runtime.loop_interval_seconds",
            "jukebox.playback.pause_delay_seconds",
        ),
        validator=validate_loop_interval_lower_than_pause_delay,
    ),
)


def get_rules_affected_by_paths(dotted_paths: Iterable[str]) -> list[SettingsValidationRule]:
    updated_paths = set(dotted_paths)
    return [
        rule
        for rule in VALIDATION_RULES
        if any(dependency_path in updated_paths for dependency_path in rule.depends_on_paths)
    ]


def get_rules_supported_by_settings(settings: Mapping[str, Any]) -> list[SettingsValidationRule]:
    return [
        rule
        for rule in VALIDATION_RULES
        if all(_has_dotted_path(settings, dependency_path) for dependency_path in rule.depends_on_paths)
    ]


def validate_settings_rules(
    settings: Mapping[str, Any],
    updated_paths: Iterable[str] | None = None,
) -> None:
    supported_rules = get_rules_supported_by_settings(settings)
    if updated_paths is None:
        rules_to_validate = supported_rules
    else:
        affected_names = {rule.name for rule in get_rules_affected_by_paths(updated_paths)}
        rules_to_validate = [rule for rule in supported_rules if rule.name in affected_names]

    for rule in rules_to_validate:
        rule.validate(settings)


def _has_dotted_path(settings: Mapping[str, Any], dotted_path: str) -> bool:
    current: Any = settings

    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False
        current = current[part]

    return True


def _get_dotted_path(settings: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = settings

    for part in dotted_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]

    return current
