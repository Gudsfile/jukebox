from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .timing_validation import (
    validate_loop_interval_lower_than_pause_delay,
    validate_pause_delay_lower_than_pause_duration,
)
from .value_providers import SettingsValueProvider


@dataclass(frozen=True)
class SettingsValidationRule:
    name: str
    depends_on_paths: tuple[str, ...]
    validator: Callable[..., None]

    def validate(self, provider: SettingsValueProvider) -> None:
        values = [provider.get_value(dotted_path) for dotted_path in self.depends_on_paths]
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
    SettingsValidationRule(
        name="pause_delay_lower_than_pause_duration",
        depends_on_paths=(
            "jukebox.playback.pause_delay_seconds",
            "jukebox.playback.pause_duration_seconds",
        ),
        validator=validate_pause_delay_lower_than_pause_duration,
    ),
)


def get_rules_affected_by_paths(dotted_paths: Iterable[str]) -> list[SettingsValidationRule]:
    updated_paths = set(dotted_paths)
    return [
        rule
        for rule in VALIDATION_RULES
        if any(dependency_path in updated_paths for dependency_path in rule.depends_on_paths)
    ]


def get_rules_supported_by_provider(provider: SettingsValueProvider) -> list[SettingsValidationRule]:
    return [
        rule
        for rule in VALIDATION_RULES
        if all(provider.has_value(dependency_path) for dependency_path in rule.depends_on_paths)
    ]


def validate_settings_rules(
    provider: SettingsValueProvider,
    updated_paths: Optional[Iterable[str]] = None,
) -> None:
    supported_rules = get_rules_supported_by_provider(provider)
    if updated_paths is None:
        rules_to_validate = supported_rules
    else:
        affected_names = {rule.name for rule in get_rules_affected_by_paths(updated_paths)}
        rules_to_validate = [rule for rule in supported_rules if rule.name in affected_names]

    for rule in rules_to_validate:
        rule.validate(provider)
